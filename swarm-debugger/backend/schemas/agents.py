from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from backend.schemas.execution import ExecutionResult


class ProsecutorResult(BaseModel):
    """
    Forensic artifact produced by Prosecutor Agent.
    Investigates the failure, isolates the root cause, and proposes Fix A.
    """
    root_cause: str = Field(..., description="Pinpointed failure mechanism / root cause")
    evidence: List[str] = Field(..., description="Forensic evidence items supporting the indictment")
    affected_files: List[str] = Field(default_factory=list, description="List of source files involved")
    proposed_patch: str = Field(..., description="Candidate patch diff (Fix A)")
    reasoning_summary: str = Field(
        ..., 
        description="Concise reasoning artifact (no raw chain-of-thought exposed)"
    )


class DefenderResult(BaseModel):
    """
    Forensic artifact produced by Defender Agent.
    Challenges Prosecutor's hypothesis, prevents regressions, and proposes Fix B.
    """
    challenge: str = Field(..., description="Challenge against Prosecutor's hypothesis")
    alternative_hypothesis: str = Field(..., description="Alternative explanation or edge-case vulnerability")
    evidence: List[str] = Field(..., description="Counter-evidence or regression risk items")
    affected_files: List[str] = Field(default_factory=list, description="List of source files involved")
    proposed_patch: str = Field(..., description="Alternative candidate patch diff (Fix B)")
    reasoning_summary: str = Field(
        ...,
        description="Concise reasoning artifact (no raw chain-of-thought exposed)"
    )


class JudgeExecutionDetails(BaseModel):
    """Execution evidence container for both candidate patches."""
    patch_a: ExecutionResult = Field(..., description="Sandbox execution proof for Patch A")
    patch_b: ExecutionResult = Field(..., description="Sandbox execution proof for Patch B")


class JudgeResult(BaseModel):
    """
    Judicial decision produced by Judge Agent.
    Adjudicates strictly based on isolated sandbox test executions.
    Never declares VERIFIED based on LLM confidence or rhetoric.
    """
    decision: Literal["VERIFIED", "CONTINUE", "UNRESOLVED", "MULTIPLE_VALID_FIXES"] = Field(
        ..., description="Judicial verdict status"
    )
    winning_patch: Optional[Literal["A", "B"]] = Field(
        None, description="Winner confirmed by test execution ('A' or 'B')"
    )
    reason: str = Field(..., description="Judicial explanation referencing test execution truth")
    execution: JudgeExecutionDetails = Field(
        ..., description="Execution proofs for both Patch A and Patch B"
    )
