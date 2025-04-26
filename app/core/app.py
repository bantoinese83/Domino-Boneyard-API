"""Application factory module."""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import API_VERSION, LOG_FORMAT, CORS_ORIGINS, CORS_ALLOW_CREDENTIALS
from app.api.router import api_router
from app.api.errors import register_exception_handlers

# Configure logging
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """
    Application factory pattern to create a configured FastAPI instance.
    """
    # Create FastAPI app with metadata
    app = FastAPI(
        title="Dominoes API",
        description="A RESTful API for managing domino games with real-time WebSocket updates. Sets expire after 14 days of inactivity.",
        version=API_VERSION,
        # Define explicit responses for common errors in OpenAPI docs
        responses={
            404: {"description": "Resource Not Found"},
            400: {"description": "Bad Request (e.g., invalid input)"},
            409: {"description": "Conflict (e.g., not enough tiles)"},
        }
    )

    # Register error handlers
    register_exception_handlers(app)

    # Add CORS middleware with configuration from environment variables
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files directory
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Include all routes
    app.include_router(api_router)

    # Add root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": f"Welcome to the Dominoes API v{API_VERSION}. See /docs for details."}

    return app 