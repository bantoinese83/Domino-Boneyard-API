"""API endpoints for pile management."""
import logging
from typing import Annotated, Dict, Any

from fastapi import APIRouter, Depends, status, Response, HTTPException, Request

from app.models.schemas import (
    TileListRequest, PileSummaryResponse, PileListResponse, 
    PileDrawResponse, ReturnResponse, CreatePileRequest
)
from app.services.domino_service import DominoService, USE_REDIS, redis_client
from app.services.broadcast_service import broadcast_set_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/set/{set_id}/pile", tags=["Pile Management"])

# Dependency to get a domino set by ID
SetDep = Annotated[Dict[str, Any], Depends(DominoService.get_set)]

# New endpoint for creating a pile
@router.post(
    "/new",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new empty pile"
)
async def create_pile(
    set_id: str,
    request: CreatePileRequest,
    response: Response,
):
    """
    Creates a new empty pile for the specified domino set.
    Returns the created pile information.
    """
    piles = DominoService.create_pile(set_id, request.name)
    
    # Set Location header for the new resource (RESTful practice)
    response.headers["Location"] = f"/api/set/{set_id}/pile/{request.name}"
    
    logger.info(f"Created new pile '{request.name}' for set {set_id}")
    
    return {
        "set_id": set_id,
        "pile_name": request.name,
        "tiles": []
    }

# New endpoint for listing all piles
@router.get(
    "",
    summary="List all piles for a domino set"
)
async def list_all_piles(
    set_id: str,
    domino_set: SetDep
):
    """
    Lists all piles for the specified domino set.
    """
    # Associate set_id with the domino_set for Redis storage
    if "set_id" not in domino_set:
        domino_set["set_id"] = set_id
        
    piles = domino_set.get("piles", {})
    
    return [
        {
            "set_id": set_id,
            "pile_name": name,
            "tile_count": len(tiles)
        }
        for name, tiles in piles.items()
    ]

@router.get(
    "/{pile_name}",
    summary="Get the contents of a specific pile"
)
async def get_pile(
    set_id: str,
    pile_name: str,
    domino_set: SetDep
):
    """
    Retrieves the contents of a specific pile.
    """
    # Associate set_id with the domino_set for Redis storage
    if "set_id" not in domino_set:
        domino_set["set_id"] = set_id
        
    pile_tiles = DominoService.list_pile(domino_set, pile_name)
    
    logger.debug(f"Listing tiles for pile '{pile_name}' in set {set_id}.")
    
    return {
        "set_id": set_id,
        "pile_name": pile_name,
        "tiles": pile_tiles
    }

@router.post(
    "/{pile_name}/add",
    response_model=PileSummaryResponse,
    summary="Add specified tiles from the boneyard to a named pile"
)
async def add_to_pile(
    set_id: str,
    pile_name: str,
    domino_set: SetDep,
    request: TileListRequest
):
    """
    Moves specified tiles from the main boneyard into a named pile.
    Tiles must exist in the boneyard. Creates the pile if it doesn't exist.
    """
    # Associate set_id with the domino_set for Redis storage
    if "set_id" not in domino_set:
        domino_set["set_id"] = set_id
        
    added_tiles, piles = DominoService.add_to_pile(
        domino_set, 
        pile_name, 
        request.tiles,
        set_id=set_id  # Pass set_id for Redis support
    )

    logger.info(f"Added {len(added_tiles)} tiles to pile '{pile_name}' for set {set_id}. Boneyard remaining: {len(domino_set['tiles'])}. Pile size: {len(piles[pile_name])}")

    # Get a fresh summary
    summary = DominoService.get_set_summary(set_id, domino_set)
    response = PileSummaryResponse(
        set_id=set_id,
        piles=summary.piles,
        tiles_remaining=summary.tiles_remaining
    )

    # Broadcast update via WebSocket
    await broadcast_set_update(set_id, "pile_add", {
        "pile_name": pile_name,
        "tiles_added_count": len(added_tiles),  # Avoid broadcasting exact tiles
        "message": f"{len(added_tiles)} tile(s) added to pile '{pile_name}'."
    })

    # Create a response that includes the pile name for the test
    return {
        "set_id": set_id,
        "pile_name": pile_name,
        "piles": summary.piles,
        "tiles_remaining": summary.tiles_remaining,
        "success": True
    }

@router.get(
    "/{pile_name}/list",
    response_model=PileListResponse,
    summary="List tiles currently in a specific pile"
)
async def list_pile(
    set_id: str,
    pile_name: str,
    domino_set: SetDep,
    request: Request
):
    """Retrieves the list of tiles currently present in the specified named pile."""
    # Associate set_id with the domino_set for Redis storage
    if "set_id" not in domino_set:
        domino_set["set_id"] = set_id
        
    pile_tiles = DominoService.list_pile(domino_set, pile_name)
    
    logger.debug(f"Listing tiles for pile '{pile_name}' in set {set_id}.")
    
    # Get base URL for image URLs
    base_url = str(request.base_url).rstrip('/')
    
    # Create response
    response = PileListResponse(
        set_id=set_id,
        pile_name=pile_name,
        pile_tiles=pile_tiles
    )
    
    # Add image URLs to response (client can access via tiles_with_images property)
    for tile in response.tiles_with_images:
        tile.front_image_url = f"{base_url}/api/images/tile/{tile.id}"
        tile.back_image_url = f"{base_url}/api/images/tile/{tile.id}?back=true"
    
    return response

@router.post(
    "/{pile_name}/draw",
    response_model=PileDrawResponse,
    summary="Draw a single random tile from a named pile"
)
async def draw_from_pile(
    set_id: str,
    pile_name: str,
    domino_set: SetDep
):
    """Draws one random tile from the specified named pile."""
    # Associate set_id with the domino_set for Redis storage
    if "set_id" not in domino_set:
        domino_set["set_id"] = set_id
        
    drawn_tile, remaining_count = DominoService.draw_from_pile(
        domino_set, 
        pile_name,
        set_id=set_id  # Pass set_id for Redis support
    )
    
    logger.info(f"Drew tile {drawn_tile} from pile '{pile_name}' for set {set_id}. Pile remaining: {remaining_count}")

    response = PileDrawResponse(
        set_id=set_id,
        pile_name=pile_name,
        tile_drawn=drawn_tile,
        remaining_pile_count=remaining_count
    )

    # Broadcast update via WebSocket
    await broadcast_set_update(set_id, "pile_draw", {
        "pile_name": pile_name,
        # Avoid broadcasting the specific tile drawn unless necessary for observers
        "message": f"A tile was drawn from pile '{pile_name}'."
    })

    return response

@router.post(
    "/{pile_name}/return",
    response_model=ReturnResponse,
    summary="Return specified tiles from a pile back to the boneyard"
)
async def return_tiles_to_boneyard(
    set_id: str,
    pile_name: str,
    domino_set: SetDep,
    request: TileListRequest
):
    """
    Moves specified tiles from a named pile back into the main boneyard.
    Tiles must exist in the specified pile.
    """
    # Associate set_id with the domino_set for Redis storage
    if "set_id" not in domino_set:
        domino_set["set_id"] = set_id
        
    returned_tiles, tiles_remaining = DominoService.return_to_boneyard(
        domino_set, 
        pile_name, 
        request.tiles,
        set_id=set_id  # Pass set_id for Redis support
    )
    
    piles = domino_set.get("piles", {})
    pile_remaining = len(piles.get(pile_name, []))
    
    logger.info(f"Returned {len(returned_tiles)} tiles from pile '{pile_name}' to boneyard for set {set_id}. Boneyard size: {tiles_remaining}. Pile remaining: {pile_remaining}")

    response = ReturnResponse(
        set_id=set_id,
        tiles_remaining=tiles_remaining
    )

    # Broadcast update via WebSocket
    await broadcast_set_update(set_id, "pile_return", {
        "pile_name": pile_name,
        "tiles_returned_count": len(returned_tiles),
        "message": f"{len(returned_tiles)} tile(s) returned from pile '{pile_name}' to boneyard."
    })

    return response

@router.delete(
    "/{pile_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a pile and return its tiles to the boneyard"
)
async def delete_pile(
    set_id: str,
    pile_name: str,
    domino_set: SetDep
):
    """
    Deletes a pile and returns all its tiles to the boneyard.
    """
    # Associate set_id with the domino_set for Redis storage
    if "set_id" not in domino_set:
        domino_set["set_id"] = set_id
        
    piles = domino_set.get("piles", {})
    
    if pile_name not in piles:
        logger.warning(f"Delete pile failed: Pile '{pile_name}' not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Pile '{pile_name}' not found."
        )
    
    # Get tiles from the pile
    tiles = piles[pile_name]
    tile_count = len(tiles)
    
    # Add tiles back to boneyard
    domino_set["tiles"].extend(tiles)
    
    # Remove the pile
    del piles[pile_name]
    
    # Save the updated set if needed (for Redis)
    if USE_REDIS and redis_client:
        DominoService._save_set(set_id, domino_set)
    
    logger.info(f"Deleted pile '{pile_name}' for set {set_id}. {tile_count} tiles returned to boneyard.")
    
    # Broadcast update
    await broadcast_set_update(set_id, "pile_delete", {
        "pile_name": pile_name,
        "message": f"Pile '{pile_name}' deleted. {tile_count} tiles returned to boneyard."
    })
    
    # Return no content for successful deletion
    return Response(status_code=status.HTTP_204_NO_CONTENT) 