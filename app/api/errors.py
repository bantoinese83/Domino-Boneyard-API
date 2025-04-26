"""Error handlers for the API."""
import logging
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.schemas import ErrorResponse

logger = logging.getLogger(__name__)

def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for the application."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_, exc: HTTPException):
        """Custom handler for FastAPI's HTTPException."""
        logger.warning(f"HTTPException: Status Code: {exc.status_code}, Detail: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error=f"HTTP Error: {exc.status_code}", detail=exc.detail).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(_, exc: Exception):
        """Handler for unexpected server errors."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)  # Log the full traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(error="Internal Server Error", detail="An unexpected error occurred.").model_dump(),
        ) 