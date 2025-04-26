"""WebSocket routes for real-time updates."""
import contextlib
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.services.domino_service import DominoService, domino_sets
from app.services.websocket_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/set/{set_id}")
async def websocket_endpoint(websocket: WebSocket, set_id: str):
    """WebSocket endpoint for real-time updates on a specific domino set."""
    # Check if set exists *before* accepting connection
    if set_id not in domino_sets:
        await websocket.accept()  # Accept to send error message
        await websocket.send_json({
            "event": "error",
            "data": {"message": f"Set with id '{set_id}' not found or has expired."}
        })
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning(f"WebSocket connection rejected for non-existent set_id: {set_id}")
        return

    await connection_manager.connect(websocket, set_id)
    
    try:
        # Get set data *after* connecting
        domino_set = DominoService.get_set(set_id)
        
        # Send initial state
        summary = DominoService.get_set_summary(set_id, domino_set)
        await websocket.send_json({
            "event": "connected",
            "data": {
                "message": f"Successfully connected to domino set '{set_id}'.",
                "state": summary.model_dump()
            }
        })

        # Keep connection alive (FastAPI handles ping/pong implicitly)
        # You could add handling for messages *from* the client here if needed
        while True:
            # Wait for messages or disconnect
            data = await websocket.receive_text()
            # Right now, we just log received messages and don't process them
            logger.debug(f"Received text from client for set {set_id}: {data} (Ignoring)")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected (client initiated) for set {set_id}.")
        connection_manager.disconnect(websocket, set_id)
    except Exception as e:
        # Catch unexpected errors during WebSocket handling
        logger.error(f"Unexpected error in WebSocket connection for set {set_id}: {e}", exc_info=True)
        connection_manager.disconnect(websocket, set_id)
        # Attempt to close gracefully if possible
        with contextlib.suppress(Exception):
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR) 