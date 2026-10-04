from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

# Canonical event names supported by Swarm Debugger
DebugEventType = Literal[
    "session_created",
    "session_started",
    "round_started",
    "agent_started",
    "agent_completed",
    "execution_started",
    "execution_completed",
    "evidence_created",
    "judge_started",
    "judge_completed",
    "round_completed",
    "verification_completed",
    "session_completed",
    "session_stopped",
    "error"
]


class DebugEvent(BaseModel):
    """
    Standard event envelope broadcasted over WebSocket to client frontends.
    Strictly conforms to the DebugEvent contract.
    """
    event: str = Field(
        ..., 
        description="Event type name (e.g. session_started, agent_started, execution_completed, judge_completed, verification_completed)"
    )
    session_id: str = Field(..., description="Target session identifier")
    round: Optional[int] = Field(None, description="Active round sequence number")
    agent: Optional[str] = Field(None, description="Emitting agent role or system entity")
    payload: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Strongly typed event payload dictionary containing concise artifacts or execution proofs"
    )


# Alias for backward compatibility
WebSocketEvent = DebugEvent
