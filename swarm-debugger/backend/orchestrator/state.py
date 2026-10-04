import asyncio
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
from backend.schemas.session import Session


class SessionStateManager:
    """
    In-memory state and active WebSocket connection registry.
    """

    def __init__(self):
        # session_id -> active Session object
        self._active_sessions: Dict[str, Session] = {}
        # session_id -> set of active WebSockets
        self._connections: Dict[str, Set[WebSocket]] = {}
        # session_id -> asyncio.Task running the orchestrator loop
        self._running_tasks: Dict[str, asyncio.Task] = {}
        # session_id -> stop event flag
        self._stop_events: Dict[str, asyncio.Event] = {}

    def register_session(self, session: Session):
        self._active_sessions[session.session_id] = session
        if session.session_id not in self._connections:
            self._connections[session.session_id] = set()
        self._stop_events[session.session_id] = asyncio.Event()

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._active_sessions.get(session_id)

    def register_connection(self, session_id: str, websocket: WebSocket):
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(websocket)

    def remove_connection(self, session_id: str, websocket: WebSocket):
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)

    async def broadcast(self, session_id: str, message: Dict[str, Any]):
        """Broadcasts WebSocket event payload to all clients connected to the session."""
        sockets = list(self._connections.get(session_id, []))
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                self.remove_connection(session_id, ws)

    def is_stopped(self, session_id: str) -> bool:
        event = self._stop_events.get(session_id)
        return event.is_set() if event else False

    def request_stop(self, session_id: str):
        if session_id in self._stop_events:
            self._stop_events[session_id].set()


state_manager = SessionStateManager()
