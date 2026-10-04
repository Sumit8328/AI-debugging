import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database.database import init_db
from backend.api.routes import api_router
from backend.api.websocket import ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("swarm-debugger")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for DB setup and graceful shutdown."""
    logger.info("Initializing Swarm Debugger database schema...")
    init_db()
    logger.info("Swarm Debugger backend online.")
    yield
    logger.info("Swarm Debugger shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Adversarial multi-agent debugging system: AI can argue about the bug. The code decides who is right.",
    lifespan=lifespan
)

# Enable CORS for local Vite React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.ai.client import get_openai_client

# Register REST and WebSocket routers
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    """Health check alias on root app."""
    client = get_openai_client()
    return {
        "status": "ok",
        "openai_configured": client.is_configured(),
        "model": client.model_name
    }


@app.get("/")
async def root():
    return {
        "system": settings.PROJECT_NAME,
        "tagline": "AI can argue about the bug. The code decides who is right.",
        "status": "ready",
        "version": settings.VERSION,
        "docs": "/docs",
        "endpoints": {
            "create_session": "POST /api/sessions",
            "start_session": "POST /api/sessions/{session_id}/start",
            "get_session": "GET /api/sessions/{session_id}",
            "stop_session": "POST /api/sessions/{session_id}/stop",
            "websocket_events": "WS /api/sessions/{session_id}/events",
            "demos": "GET /api/demos"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
