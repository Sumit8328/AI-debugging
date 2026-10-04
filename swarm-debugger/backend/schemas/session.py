from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from backend.schemas.agents import ProsecutorResult, DefenderResult, JudgeResult
from backend.schemas.execution import ExecutionResult


RoundStatus = Literal["pending", "running", "completed", "failed"]


class RoundState(BaseModel):
    """
    Contract representing the state and artifacts of a single adversarial debate round.
    """
    round_number: int = Field(..., description="Round sequence number (1-based)")
    prosecutor_result: Optional[ProsecutorResult] = Field(default=None, description="Prosecutor candidate Fix A artifact")
    defender_result: Optional[DefenderResult] = Field(default=None, description="Defender candidate Fix B artifact")
    patch_a_execution: Optional[ExecutionResult] = Field(default=None, description="Actual sandbox execution proof for Patch A")
    patch_b_execution: Optional[ExecutionResult] = Field(default=None, description="Actual sandbox execution proof for Patch B")
    judge_result: Optional[JudgeResult] = Field(default=None, description="Judicial evaluation based on execution proofs")
    status: RoundStatus = Field(default="pending", description="Lifecycle status of this round")
    failed_evidence_carried_over: Optional[str] = Field(default=None, description="Failure traces carried forward into this round")


class SessionCreateRequest(BaseModel):
    """Request payload to initialize a new debugging session."""
    bug_description: str = Field(..., description="Description of the bug / failure")
    test_command: str = Field(default="pytest", description="Command used to reproduce and verify fixes")
    max_rounds: int = Field(default=3, ge=1, le=10, description="Max debate rounds")
    demo_id: Optional[str] = Field(default=None, description="Selected demo project ID if applicable")
    repository_path: Optional[str] = Field(default=None, description="Custom project directory")


class SessionResponse(BaseModel):
    """Standardized API response for session lifecycle events."""
    session_id: str = Field(..., description="Unique session identifier")
    status: str = Field(..., description="Current session status")
    bug_description: str = Field(..., description="Reported bug description")
    test_command: str = Field(..., description="Test command for reproduction")
    current_round: int = Field(..., description="Current active round number")
    max_rounds: int = Field(..., description="Maximum rounds configured")


class Session(BaseModel):
    """
    Complete state model representing an adversarial debugging session.
    """
    session_id: str = Field(..., description="Unique UUID or identifier for the debugging session")
    status: str = Field(default="idle", description="Current lifecycle state of the session")
    bug_description: str = Field(..., description="User-reported symptom or bug description")
    test_command: str = Field(default="pytest", description="Command used to reproduce and verify fixes")
    current_round: int = Field(default=1, description="Current active round index (1-based)")
    max_rounds: int = Field(default=3, description="Maximum adversarial debate rounds before timeout")
    
    repository_path: Optional[str] = Field(default=None, description="Path or demo id of repository under test")
    demo_id: Optional[str] = Field(default=None, description="Selected demo project ID if applicable")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rounds: List[RoundState] = Field(default_factory=list, description="Historical debate rounds")
    verified_patch: Optional[str] = Field(default=None, description="Unified diff of verified patch if successful")
    winning_patch: Optional[Literal["A", "B"]] = Field(default=None, description="Winning patch ('A' or 'B')")
