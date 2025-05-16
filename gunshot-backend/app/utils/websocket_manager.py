from fastapi import WebSocket, APIRouter, WebSocketDisconnect
import asyncio
import logging
from weakref import WeakSet

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections = WeakSet()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        async with self.lock:
            disconnected_clients = []
            for ws in self.active_connections:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to WebSocket: {e}")
                    disconnected_clients.append(ws)
            for ws in disconnected_clients:
                await self.disconnect(ws)

    async def disconnect_all(self):
        async with self.lock:
            for ws in self.active_connections:
                await ws.close()
            self.active_connections.clear()

manager = WebSocketManager()