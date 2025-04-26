"""Service for broadcasting updates via WebSockets."""
import logging
from typing import Dict, Any

from app.services.domino_service import DominoService, domino_sets
from app.services.websocket_manager import connection_manager

logger = logging.getLogger(__name__)

async def broadcast_set_update(set_id: str, event: str, event_data: Dict[str, Any]):
    """
    Helper to get summary and broadcast WebSocket update.
    
    Args:
        set_id: The ID of the domino set
        event: The event type (e.g., 'shuffle', 'draw')
        event_data: Additional data for the event
    """
    if set_id in domino_sets:  # Check if set still exists before broadcasting
        domino_set = domino_sets[set_id]
        summary = DominoService.get_set_summary(set_id, domino_set)
        message = {
            "event": event,
            "data": {**event_data, "state": summary.model_dump()}  # Use model_dump() for Pydantic v2
        }
        await connection_manager.broadcast(set_id, message) 