import uuid
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException

from backend.schemas.session import Session, SessionCreateRequest, SessionResponse
from backend.database.models import SessionRepository
from backend.orchestrator.state import state_manager
from backend.orchestrator.engine import OrchestratorEngine
from backend.repository.scanner import RepositoryScanner
from backend.repository.loader import RepositoryLoader
from backend.ai.client import get_openai_client
from backend.config import settings

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
async def health_check():
    """
    GET /api/health
    Returns OpenAI integration status.
    IMPORTANT: Never exposes the API key.
    """
    client = get_openai_client()
    return {
        "status": "ok",
        "openai_configured": client.is_configured(),
        "model": client.model_name
    }


@api_router.get("/demos")
async def list_demos():
    """Returns preset demo projects for immediate hackathon verification."""
    return [
        {
            "id": "bug-01",
            "title": "Batch Slicing Off-by-One Overflow",
            "description": "IndexError and boundary leak when batch slicing collection whose length matches multiple of batch size.",
            "test_command": "pytest test_processor.py",
            "files": ["processor.py", "test_processor.py"]
        },
        {
            "id": "bug-02",
            "title": "Default Mutable Argument State Bleed",
            "description": "Shared list accumulator retains data across consecutive function calls in multi-threaded query builder.",
            "test_command": "pytest test_accumulator.py",
            "files": ["accumulator.py", "test_accumulator.py"]
        },
        {
            "id": "bug-03",
            "title": "RegEx Tokenizer ReDoS & Escape Failure",
            "description": "Regex fails on unescaped brackets and catastrophic backtracking on malformed input strings.",
            "test_command": "pytest test_tokenizer.py",
            "files": ["tokenizer.py", "test_tokenizer.py"]
        }
    ]


@api_router.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest):
    """
    POST /api/sessions
    Creates a new debugging session from SessionCreateRequest.
    Returns SessionResponse.
    """
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    new_session = Session(
        session_id=session_id,
        status="idle",
        bug_description=request.bug_description,
        test_command=request.test_command,
        current_round=1,
        max_rounds=request.max_rounds,
        demo_id=request.demo_id,
        repository_path=request.repository_path or request.demo_id
    )

    SessionRepository.create_session(new_session)
    state_manager.register_session(new_session)
    return SessionResponse(
        session_id=new_session.session_id,
        status=new_session.status,
        bug_description=new_session.bug_description,
        test_command=new_session.test_command,
        current_round=new_session.current_round,
        max_rounds=new_session.max_rounds
    )


@api_router.post("/sessions/{session_id}/start", response_model=SessionResponse)
async def start_session(session_id: str):
    """
    POST /api/sessions/{session_id}/start
    Triggers execution of the adversarial multi-agent debate loop.
    Returns SessionResponse.
    """
    session = state_manager.get_session(session_id) or SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status not in ("debating", "executing"):
        session.status = "debating"
        engine = OrchestratorEngine(session)
        asyncio.create_task(engine.run())

    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        bug_description=session.bug_description,
        test_command=session.test_command,
        current_round=session.current_round,
        max_rounds=session.max_rounds
    )


@api_router.get("/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """
    GET /api/sessions/{session_id}
    Retrieves complete session state including all round states and execution proofs.
    """
    session = state_manager.get_session(session_id) or SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@api_router.post("/sessions/{session_id}/stop", response_model=SessionResponse)
async def stop_session(session_id: str):
    """
    POST /api/sessions/{session_id}/stop
    Stops a running adversarial debate session.
    Returns SessionResponse.
    """
    session = state_manager.get_session(session_id) or SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    state_manager.request_stop(session_id)
    SessionRepository.update_session_status(session_id, "stopped")
    session.status = "stopped"

    return SessionResponse(
        session_id=session.session_id,
        status="stopped",
        bug_description=session.bug_description,
        test_command=session.test_command,
        current_round=session.current_round,
        max_rounds=session.max_rounds
    )


@api_router.get("/sessions/{session_id}/codebase")
async def get_session_codebase(session_id: str):
    """Returns scanned codebase tree and files for the session."""
    session = state_manager.get_session(session_id) or SessionRepository.get_session(session_id)
    demo_id = (session.demo_id if session else None) or "bug-01"
    repo_path, files = RepositoryLoader.load_demo(demo_id)
    tree = RepositoryScanner.scan_structure(repo_path)
    return {
        "tree": tree,
        "files": files
    }
