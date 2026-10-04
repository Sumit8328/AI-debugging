import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.orchestrator.state import state_manager
from backend.database.models import SessionRepository
from backend.schemas.events import DebugEvent

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/api/sessions/{session_id}/events")
async def websocket_session_events(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time live streaming of debate artifacts,
    test executions, and judicial verdicts via strongly typed DebugEvent objects.
    """
    await websocket.accept()
    state_manager.register_connection(session_id, websocket)
    logger.info(f"WebSocket client connected to session: {session_id}")

    try:
        # Send current session snapshot on connect as session_created/session_started DebugEvent
        session = state_manager.get_session(session_id) or SessionRepository.get_session(session_id)
        if session:
            init_event = DebugEvent(
                event="session_created" if session.status == "idle" else "session_started",
                session_id=session_id,
                round=session.current_round,
                agent="system",
                payload={
                    "status": session.status,
                    "bug_description": session.bug_description,
                    "test_command": session.test_command,
                    "current_round": session.current_round,
                    "max_rounds": session.max_rounds,
                    "rounds": [r.model_dump() for r in session.rounds]
                }
            )
            await websocket.send_json(init_event.model_dump())

        while True:
            # Keep connection alive and accept client control messages / ping
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    pong_event = DebugEvent(
                        event="pong",
                        session_id=session_id,
                        round=0,
                        agent="system",
                        payload={"status": "alive"}
                    )
                    await websocket.send_json(pong_event.model_dump())
            except Exception:
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from session: {session_id}")
    except Exception as e:
        logger.warning(f"WebSocket error for session {session_id}: {e}")
    finally:
        state_manager.remove_connection(session_id, websocket)
