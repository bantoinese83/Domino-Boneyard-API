"""API endpoints for serving domino tile images."""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import RedirectResponse

from app.models.schemas import TileInfo
from app.services.domino_service import DominoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["Images"])

@router.get(
    "/tile/{tile_id}",
    summary="Get the image for a specific domino tile"
)
async def get_tile_image(
    tile_id: str,
    back: Optional[bool] = False
):
    """
    Returns a redirect to the static image file for the requested domino tile.
    
    Args:
        tile_id: The ID of the tile (e.g., "01", "66")
        back: If true, returns the back of the tile instead of the front
    
    Returns:
        A redirect to the static image file
    """
    if back:
        # Return the back of the tile
        return RedirectResponse(url="/static/images/tiles/domino-backs/domino-back.png")

    # Parse the tile ID
    if len(tile_id) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tile ID must be exactly 2 characters (e.g., '01', '66')"
        )

    try:
        # Extract the two numbers
        num1 = int(tile_id[0])
        num2 = int(tile_id[1])

        # Domino tiles are canonical with the smaller number first
        # But our image filenames have the larger number second
        min_val = min(num1, num2)
        max_val = max(num1, num2)

        # Construct the URL for the front of the tile
        image_url = f"/static/images/tiles/domino-fronts/domino-{min_val}-{max_val}.png"

        return RedirectResponse(url=image_url)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tile ID must contain only digits (e.g., '01', '66')",
        ) from e

@router.get(
    "/tiles",
    summary="Get information about all available tiles",
    response_model=List[TileInfo]
)
async def get_all_tiles(request: Request):
    """
    Returns information about all available domino tiles, including their image URLs.
    
    Returns:
        A list of TileInfo objects, each containing the tile ID and image URLs
    """
    # Get the base URL for the request
    base_url = str(request.base_url).rstrip('/')
    
    # Get the set type (default to double-six)
    set_type = "double-six"
    
    # Generate all tile IDs for this set type
    tiles = DominoService.generate_tiles(set_type)
    
    # Create TileInfo objects for each tile
    return [TileInfo.from_tile_id(tile, base_url) for tile in tiles] 