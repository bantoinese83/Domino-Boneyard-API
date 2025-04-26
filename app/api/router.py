"""Main API router that includes all endpoint routers."""
from fastapi import APIRouter

from app.api.endpoints import sets, piles, websockets, images

# Main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(sets.router)
api_router.include_router(piles.router)
api_router.include_router(websockets.router)
api_router.include_router(images.router) 