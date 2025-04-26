"""API endpoints for domino set management."""
import logging
from typing import Annotated, Dict, Any, List

from fastapi import APIRouter, Depends, Query, HTTPException, status, Response, Request

from app.models.schemas import (
    CreateSetRequest, DrawRequest, SetResponse, ShuffleResponse, DrawResponse, SetSummary
)
from app.services.domino_service import DominoService
from app.services.broadcast_service import broadcast_set_update
from app.core.config import USE_REDIS, VALID_DOMINO_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/set", tags=["Set Management"])

# Dependency to get a domino set by ID
SetDep = Annotated[Dict[str, Any], Depends(DominoService.get_set)]

@router.get(
    "",
    summary="List all active domino sets",
    response_model=List[SetSummary]
)
async def list_sets():
    """
    Lists all active domino sets in the system that haven't expired.
    This is useful for administrative purposes or reconnecting to existing games.
    """
    try:
        # Run cleanup first to remove any expired sets
        DominoService.clean_expired_sets()

        # Get all active sets (each with basic info only)
        active_sets = []
        if not USE_REDIS:
            # In-memory implementation
            for set_id, domino_set in DominoService.get_all_sets().items():
                summary = DominoService.get_set_summary(set_id, domino_set)
                active_sets.append(summary)

        return active_sets
    except Exception as e:
        logger.error(f"Error listing sets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve domino sets.",
        ) from e

@router.post(
    "/new",
    response_model=SetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new domino set"
)
async def create_new_set(request: CreateSetRequest, response: Response):
    """
    Creates a new, shuffled domino set with the specified type and number of combined sets.
    Returns the unique set ID and initial state.
    Expired sets are cleaned up periodically during creation requests.
    """
    # Check for valid set type
    if request.type not in VALID_DOMINO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid set type: {request.type}. Must be one of {VALID_DOMINO_TYPES}"
        )
        
    # Run cleanup potentially (could be moved to a background task for better performance)
    try:
        DominoService.clean_expired_sets()
    except Exception as e:
        logger.error(f"Error during expired set cleanup: {e}", exc_info=True)
        # Log but continue - don't block set creation if cleanup fails

    try:
        set_id, domino_set = DominoService.create_set(request.type, request.sets)
        
        # Set Location header for the new resource (RESTful practice)
        response.headers["Location"] = f"/api/set/{set_id}"
        
        return SetResponse(
            set_id=set_id,
            type=request.type,
            tiles_remaining=len(domino_set["tiles"])
        )
    except ValueError as e:  # Catch potential error from generate_tiles
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to create domino set: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to create domino set due to an internal error."
        )

@router.get(
    "/{set_id}",
    response_model=SetSummary,
    summary="Get the current state of a domino set"
)
async def get_set_state(set_id: str):
    """
    Retrieves the current state of a domino set, including its piles and remaining tiles.
    This is useful to synchronize state without using WebSockets.
    """
    try:
        domino_set = DominoService.get_set(set_id)
        return DominoService.get_set_summary(set_id, domino_set)
    except HTTPException:
        # Re-raise the HTTPException from get_set
        raise
    except Exception as e:
        logger.error(f"Error retrieving set {set_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve domino set state.",
        ) from e

@router.post(
    "/{set_id}/shuffle",
    response_model=ShuffleResponse,
    summary="Shuffle domino tiles"
)
async def shuffle_set(
    set_id: str,
    domino_set: SetDep,
    remaining: Annotated[bool, Query(description="If true, shuffle only the remaining tiles in the boneyard. If false, collect all tiles (boneyard + all piles) and shuffle them back into the boneyard.")] = False
):
    """
    Shuffles the tiles in the specified set. Can shuffle only remaining boneyard tiles
    or collect all tiles from boneyard and piles, shuffle, and reset piles.
    """
    try:
        # Associate set_id with the domino_set for Redis storage
        if "set_id" not in domino_set:
            domino_set["set_id"] = set_id

        shuffle_type = "remaining boneyard tiles" if remaining else "all tiles (boneyard + piles)"

        tiles_remaining = DominoService.shuffle_set(domino_set, remaining)

        # Ensure changes are saved regardless of storage type
        if "set_id" in domino_set:
            DominoService._save_set(set_id, domino_set)

        logger.info(f"Shuffled {shuffle_type} for set {set_id}. Tiles remaining: {tiles_remaining}")

        response = ShuffleResponse(
            set_id=set_id,
            tiles_remaining=tiles_remaining,
            message=f"Successfully shuffled {shuffle_type}."
        )

        # Broadcast update via WebSocket
        await broadcast_set_update(set_id, "shuffle", {
            "remaining_only": remaining,
            "message": f"Set shuffled ({shuffle_type})."
        })

        return response
    except Exception as e:
        logger.error(f"Error shuffling set {set_id}: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to shuffle domino set.",
        ) from e

@router.post(
    "/{set_id}/draw",
    response_model=DrawResponse,
    summary="Draw tiles from the boneyard"
)
async def draw_tiles(
    set_id: str,
    domino_set: SetDep,
    request: DrawRequest,
    request_base: Request
):
    """Draws a specified number of tiles from the main boneyard."""
    try:
        # Associate set_id with the domino_set for Redis storage
        if "set_id" not in domino_set:
            domino_set["set_id"] = set_id

        drawn_tiles, tiles_remaining = DominoService.draw_tiles(domino_set, request.count)

        # Ensure changes are saved regardless of storage type
        if "set_id" in domino_set:
            DominoService._save_set(set_id, domino_set)

        logger.info(f"Drew {len(drawn_tiles)} tile(s) for set {set_id}. Tiles remaining: {tiles_remaining}")

        # Get base URL for image URLs
        base_url = str(request_base.base_url).rstrip('/')

        # Create response with tile images
        response = DrawResponse(
            set_id=set_id,
            tiles_drawn=drawn_tiles,
            tiles_remaining=tiles_remaining
        )

        # Add image URLs to response (client can access via tiles_with_images property)
        for tile in response.tiles_with_images:
            tile.front_image_url = f"{base_url}/api/images/tile/{tile.id}"
            tile.back_image_url = f"{base_url}/api/images/tile/{tile.id}?back=true"

        # Broadcast update via WebSocket
        await broadcast_set_update(set_id, "draw", {
            "tiles_drawn_count": len(drawn_tiles),  # Avoid sending potentially sensitive tile data broadly
            "message": f"{len(drawn_tiles)} tile(s) drawn from boneyard."
            # Consider adding who drew the tiles if you have user context
        })

        return response
    except HTTPException as e:
        logger.warning(f"Draw failed for set {set_id}: requested {request.count}, only {len(domino_set['tiles'])} remain.")
        raise e
    except Exception as e:
        logger.error(f"Error drawing tiles from set {set_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to draw tiles from the boneyard.",
        ) from e

@router.delete(
    "/{set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a domino set"
)
async def delete_set(set_id: str):
    """
    Deletes a domino set and all its associated data.
    This can be useful to manually clean up a set that's no longer needed.
    """
    try:
        # First check if the set exists
        DominoService.get_set(set_id)  # This will raise 404 if not found
        
        # Then delete it
        DominoService.delete_set(set_id)
        
        # Broadcast the deletion event 
        await broadcast_set_update(set_id, "set_deleted", {
            "message": f"Domino set '{set_id}' has been deleted."
        })
        
        # Return no content for successful deletion
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        # Re-raise HTTP exceptions from get_set
        raise
    except Exception as e:
        logger.error(f"Error deleting set {set_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete the domino set."
        ) 