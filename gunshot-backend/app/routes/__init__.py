# app/routes/__init__.py
from .gunshot import router as gunshot_router
from .log_event import router as log_event_router
from .microphone import router as microphone_router
from .websocket import router as websocket_router

__all__ = ["gunshot_router", "log_event_router", "microphone_router", "websocket_router"]