"""WebSocket connection management service."""
import json
import logging
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, set_id: str):
        """Connect a new WebSocket client."""
        await websocket.accept()
        if set_id not in self.active_connections:
            self.active_connections[set_id] = []
        self.active_connections[set_id].append(websocket)
        logger.info(f"WebSocket connected for set {set_id}. Total clients: {len(self.active_connections[set_id])}")

    def disconnect(self, websocket: WebSocket, set_id: str):
        """Disconnect a WebSocket client."""
        if set_id in self.active_connections:
            if websocket in self.active_connections[set_id]:
                self.active_connections[set_id].remove(websocket)
                logger.info(f"WebSocket disconnected for set {set_id}.")
            if not self.active_connections[set_id]:
                del self.active_connections[set_id]
                logger.info(f"Last client disconnected for set {set_id}, removing entry.")

    async def broadcast(self, set_id: str, message: dict):
        """Broadcast a message to all connected clients for a set."""
        if set_id not in self.active_connections:
            return  # No clients for this set

        disconnected_clients = []
        message_json = json.dumps(message)  # Serialize once
        for connection in self.active_connections[set_id]:
            try:
                await connection.send_text(message_json)  # Use send_text for pre-serialized
            except Exception as e:  # Catch broader exceptions during send
                logger.warning(f"Failed to send message to client for set {set_id}: {e}. Marking for removal.")
                disconnected_clients.append(connection)

        # Clean up disconnected clients after iterating
        for client in disconnected_clients:
            self.disconnect(client, set_id)

# Global connection manager instance
connection_manager = ConnectionManager() 