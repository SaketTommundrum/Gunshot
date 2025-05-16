from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.routes.gunshot    import router as gunshot_router
from app.routes.log_event  import router as log_event_router
from app.routes.microphone import router as mic_router
from app.routes.delete_all import router as delete_all
from app.routes.get_all_logs import router as get_all_logs
from app.routes.test_points import router as test_points_router
from app.routes.websocket  import router as ws_router

app = FastAPI()

from app.utils.database import create_tables
from app.utils.database import engine

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(gunshot_router)
app.include_router(log_event_router)
app.include_router(mic_router)
app.include_router(get_all_logs)
app.include_router(test_points_router)
app.include_router(delete_all)
app.include_router(ws_router)

async def lifespan(app: FastAPI):
    # Startup: create tables
    await create_tables()
    yield
    # Shutdown: dispose engine
    print("Shutting down the application…")
    await engine.dispose()
    print("Database connections closed.")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    # you can return plain text, JSON, or HTML here
    return """
    <html>
      <head><title>Gunshot Backend</title></head>
      <body>
        <h1>Welcome to the Gunshot API</h1>
        <p>WebSocket: <code>ws://127.0.0.1:8000/ws</code></p>
      </body>
    </html>
    """