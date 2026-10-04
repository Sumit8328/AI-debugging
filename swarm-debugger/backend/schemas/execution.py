from typing import Literal
from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """
    Result of running candidate patch in isolated sandbox test runner.
    Actual test execution is the ultimate source of truth.
    Only the Docker execution layer (or deterministic mock runner) may create an ExecutionResult.
    """
    patch: Literal["A", "B"] = Field(..., description="Target candidate patch identifier ('A' or 'B')")
    status: Literal["passed", "failed", "error", "timeout"] = Field(
        ..., description="Execution outcome status"
    )
    stdout: str = Field(default="", description="Sandbox standard output")
    stderr: str = Field(default="", description="Sandbox standard error")
    exit_code: int = Field(..., description="Process exit code (0 for success)")
    tests_passed: int = Field(default=0, description="Count of passing pytest tests")
    tests_failed: int = Field(default=0, description="Count of failing pytest tests")
    duration_ms: int = Field(default=0, description="Execution duration in milliseconds")
    execution_mode: str = Field(default="docker", description="Execution engine used ('docker' or 'demo')")


class ExecutionRequest(BaseModel):
    """
    Request specification for executing a candidate patch in an isolated sandbox.
    """
    session_id: str = Field(..., description="Unique session identifier")
    round_number: int = Field(default=1, description="Current debate round number")
    patch: Literal["A", "B"] = Field(..., description="Target candidate patch identifier ('A' or 'B')")
    repository_path: str = Field(..., description="Original repository root or demo project path")
    patch_content: str = Field(..., description="Unified diff or patch content to apply")
    test_command: str = Field(default="pytest", description="Command used to verify patch")


class SandboxRunConfig(BaseModel):
    """Configuration for sandbox test execution."""
    timeout_seconds: int = 30
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    command: str = "pytest"
