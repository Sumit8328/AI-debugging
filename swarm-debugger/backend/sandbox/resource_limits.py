from pydantic import BaseModel, Field


class SandboxResourceLimits(BaseModel):
    """
    Enforced resource limits for Docker sandbox execution to prevent runaway code.
    """
    max_memory_mb: int = Field(default=512, description="Max RAM in MB allocated to container")
    cpu_limit: float = Field(default=1.0, description="Max CPU cores container can utilize")
    timeout_seconds: int = Field(default=30, description="Max test execution wall time before SIGKILL")
    network_enabled: bool = Field(default=False, description="Disable internet access inside sandbox")
    read_only_root: bool = Field(default=True, description="Enforce read-only container rootfs")
    pids_limit: int = Field(default=64, description="Max processes allowed inside container")
