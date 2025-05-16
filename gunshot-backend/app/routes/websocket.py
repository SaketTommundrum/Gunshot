from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.websocket_manager import manager
import logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                message = await websocket.receive_text()
                print(f"Received: {message}")
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
    finally:
        await manager.disconnect(websocket)