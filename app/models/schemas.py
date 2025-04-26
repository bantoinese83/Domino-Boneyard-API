"""Pydantic models for request validation and response serialization."""
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, field_validator

from app.core.config import VALID_DOMINO_TYPES

# --- Base Models ---
class BaseResponse(BaseModel):
    """Common base for successful responses."""
    success: bool = True
    set_id: str

class ErrorResponse(BaseModel):
    """Standard error response format."""
    success: bool = False
    error: str
    detail: Optional[Any] = None

class TileInfo(BaseModel):
    """Information about a domino tile, including image URLs."""
    id: str
    front_image_url: str
    back_image_url: str

    @classmethod
    def from_tile_id(cls, tile_id: str, base_url: str = "") -> "TileInfo":
        """Create a TileInfo object from a tile ID."""
        return cls(
            id=tile_id,
            front_image_url=f"{base_url}/api/images/tile/{tile_id}",
            back_image_url=f"{base_url}/api/images/tile/{tile_id}?back=true"
        )

# --- Request Models ---
class CreateSetRequest(BaseModel):
    """Request to create a new domino set."""
    type: str = Field(..., description="Type of domino set.", examples=VALID_DOMINO_TYPES)
    sets: int = Field(1, ge=1, le=10, description="Number of identical sets to combine.")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        if v not in VALID_DOMINO_TYPES:
            raise ValueError(f"Type must be one of {VALID_DOMINO_TYPES}")
        return v

class CreatePileRequest(BaseModel):
    """Request to create a new pile."""
    name: str = Field(..., description="Name of the pile to create.", examples=["player1"])

class DrawRequest(BaseModel):
    """Request to draw tiles from the boneyard."""
    count: int = Field(..., ge=1, description="Number of tiles to draw from the main boneyard.")

class TileListRequest(BaseModel):
    """Request body for operations involving a list of tiles."""
    tiles: List[str] = Field(..., min_length=1, description="List of tiles (e.g., ['12', '34']).", examples=[["01", "55"]])
    
    @field_validator('tiles')
    @classmethod
    def convert_tiles_format(cls, v):
        """Convert various input formats to the expected string format."""
        result = []
        for tile in v:
            if isinstance(tile, list) and len(tile) == 2:
                # Convert [1, 2] to "12"
                try:
                    result.append(f"{tile[0]}{tile[1]}")
                except (IndexError, TypeError):
                    raise ValueError(f"Invalid tile format: {tile}")
            elif isinstance(tile, str):
                # Already in the right format
                result.append(tile)
            else:
                raise ValueError(f"Invalid tile format: {tile}")
        return result

# --- Response Models ---
class SetResponse(BaseResponse):
    """Response after creating a new set."""
    type: str
    tiles_remaining: int
    message: str = "Domino set created successfully."

class ShuffleResponse(BaseResponse):
    """Response after shuffling tiles."""
    shuffled: bool = True
    tiles_remaining: int
    message: str

class DrawResponse(BaseResponse):
    """Response after drawing tiles."""
    tiles_drawn: List[str]
    tiles_remaining: int
    
    @property
    def tiles_with_images(self) -> List[TileInfo]:
        """Return tiles with image URLs."""
        return [TileInfo.from_tile_id(tile) for tile in self.tiles_drawn]

class PileInfo(BaseModel):
    """Details about a specific pile."""
    count: int

class PileSummaryResponse(BaseResponse):
    """Response summarizing piles after an operation."""
    piles: Dict[str, PileInfo]
    tiles_remaining: int

class PileListResponse(BaseResponse):
    """Response when listing pile contents."""
    pile_name: str
    pile_tiles: List[str]
    
    @property
    def tiles_with_images(self) -> List[TileInfo]:
        """Return tiles with image URLs."""
        return [TileInfo.from_tile_id(tile) for tile in self.pile_tiles]

class PileDrawResponse(BaseResponse):
    """Response after drawing from a pile."""
    pile_name: str
    tile_drawn: str
    remaining_pile_count: int

class ReturnResponse(BaseResponse):
    """Response after returning tiles to the boneyard."""
    tiles_remaining: int
    message: str = "Tiles returned to the main boneyard successfully."

class SetSummary(BaseModel):
    """Represents the overall state of a domino set for broadcasting."""
    set_id: str
    type: str
    tiles_remaining: int
    piles: Dict[str, PileInfo]

class WebSocketMessage(BaseModel):
    """Message format for WebSocket communication."""
    event: str
    data: Dict[str, Any] 