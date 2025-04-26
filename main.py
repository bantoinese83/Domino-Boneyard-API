"""
Domino Boneyard API - Main entry point.

This API provides endpoints for managing domino games with real-time WebSocket updates.
The refactored code follows Single Responsibility Principle with a clear separation of concerns.
"""
import os
import uvicorn

from app.core.app import create_app

# Create FastAPI application
app = create_app()

if __name__ == "__main__":
    # Get configuration from environment variables or use defaults
    host = os.getenv("DOMINO_HOST", "0.0.0.0")
    port = int(os.getenv("DOMINO_PORT", "8000"))
    # In production, reload should be False
    reload = os.getenv("DOMINO_RELOAD", "false").lower() == "true"
    log_level = os.getenv("DOMINO_LOG_LEVEL", "info").lower()
    
    uvicorn.run(
        "main:app", 
        host=host, 
        port=port, 
        reload=reload, 
        log_level=log_level
    )