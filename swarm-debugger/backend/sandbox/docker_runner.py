import os
import re
import time
import uuid
import shutil
import asyncio
import logging
import subprocess
from typing import Optional, Literal, Tuple, List

from backend.config import settings
from backend.schemas.execution import ExecutionResult, ExecutionRequest
from backend.sandbox.resource_limits import SandboxResourceLimits
from backend.sandbox.patch_validator import PatchSafetyValidator

logger = logging.getLogger(__name__)


class PytestOutputParser:
    """
    Parses pytest console output to extract accurate test counts, assertion errors,
    and failure summaries.
    """

    @staticmethod
    def parse(stdout: str, stderr: str, exit_code: int) -> Tuple[int, int]:
        """
        Parses (tests_passed, tests_failed) from pytest output.
        Handles variations:
        - '5 passed in 0.42s'
        - '1 failed, 4 passed in 0.38s'
        - '25 passed, 0 failed'
        - '23 passed, 2 failed'
        - '1 failed in 0.20s'
        - '1 error in 0.10s'
        """
        combined = (stdout or "") + "\n" + (stderr or "")
        passed = 0
        failed = 0

        # Look for standard summary line
        passed_matches = re.findall(r"(\d+)\s+passed", combined)
        if passed_matches:
            try:
                passed = int(passed_matches[-1])
            except ValueError:
                pass

        failed_matches = re.findall(r"(\d+)\s+failed", combined)
        if failed_matches:
            try:
                failed = int(failed_matches[-1])
            except ValueError:
                pass

        error_matches = re.findall(r"(\d+)\s+error", combined)
        if error_matches:
            try:
                failed += int(error_matches[-1])
            except ValueError:
                pass

        # If pytest exit code indicates failure but counts were 0
        if exit_code != 0 and failed == 0 and passed == 0:
            if any(term in combined for term in ("FAILURES", "ERROR", "Failed:", "Error:", "assert")):
                failed = 1

        # If pytest exit code is 0 but passed was 0
        if exit_code == 0 and passed == 0:
            if "PASSED" in combined:
                passed = combined.count("PASSED")

        return passed, failed


def validate_test_command(cmd: str) -> Tuple[bool, str]:
    """
    Validates that test command only executes pytest without shell injection operators.
    """
    if not cmd or not cmd.strip():
        return True, "pytest -q"

    cmd_clean = cmd.strip()
    # Check for shell metacharacters
    forbidden = [";", "&&", "||", "|", "`", "$", ">", "<", "\n", "\r", "&"]
    for char in forbidden:
        if char in cmd_clean:
            return False, f"Forbidden shell operator '{char}' in test command"

    parts = cmd_clean.split()
    if not parts:
        return True, "pytest -q"

    if parts[0] != "pytest" and not (len(parts) >= 3 and parts[0] == "python" and parts[1] == "-m" and parts[2] == "pytest"):
        return False, "Only 'pytest' commands are permitted in the isolated sandbox"

    return True, cmd_clean


class DockerSandboxRunner:
    """
    Isolated Docker sandbox runner for validating candidate patches via pytest.

    Execution Flow:
    AI PATCH -> PATCH VALIDATOR -> TEMPORARY WORKSPACE -> DOCKER CONTAINER -> PYTEST -> CAPTURE EVIDENCE -> DESTROY CONTAINER -> JUDGE

    SAFETY RULES:
    1. The AI patch NEVER executes directly on the host machine.
    2. Network is completely disabled (--network none).
    3. CPU limits (1.0 core) and memory limits (512MB) are strictly applied.
    4. Process limits (--pids-limit 64) prevent fork bombs.
    5. Containers are automatically removed (--rm and explicit cleanup in finally).
    6. Host filesystem is NEVER mounted except the prepared temporary candidate workspace.
    7. No host credentials or environment variables (.env, SSH keys, API keys) are mounted.
    """

    def __init__(
        self,
        limits: Optional[SandboxResourceLimits] = None,
        image_name: Optional[str] = None
    ):
        self.limits = limits or SandboxResourceLimits(
            max_memory_mb=512,
            cpu_limit=settings.SANDBOX_CPU_LIMIT or 1.0,
            timeout_seconds=settings.SANDBOX_TIMEOUT_SECONDS or 30,
            network_enabled=False,
            read_only_root=False,
            pids_limit=64
        )
        self.image = image_name or settings.DOCKER_IMAGE or "swarm-sandbox:latest"

    @classmethod
    def is_docker_available(cls) -> bool:
        """
        Verifies whether the Docker binary is installed and the Docker daemon is responding.
        """
        docker_cmd = shutil.which("docker")
        if not docker_cmd:
            return False
        try:
            res = subprocess.run(
                [docker_cmd, "info"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return res.returncode == 0
        except Exception:
            return False

    def is_image_available(self, image_name: Optional[str] = None) -> bool:
        """Checks if the required Docker sandbox image is built locally."""
        img = image_name or self.image
        docker_cmd = shutil.which("docker")
        if not docker_cmd:
            return False
        try:
            res = subprocess.run(
                [docker_cmd, "image", "inspect", img],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return res.returncode == 0
        except Exception:
            return False

    def build_sandbox_image(self, dockerfile_path: str = "docker/Dockerfile") -> Tuple[bool, str]:
        """Builds the minimal sandbox Docker image."""
        docker_cmd = shutil.which("docker")
        if not docker_cmd:
            return False, "DOCKER STATUS: NOT AVAILABLE"
        try:
            logger.info(f"Building Docker sandbox image '{self.image}' from {dockerfile_path}...")
            res = subprocess.run(
                [docker_cmd, "build", "-t", self.image, "-f", dockerfile_path, "."],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                text=True
            )
            if res.returncode == 0:
                logger.info(f"Docker sandbox image '{self.image}' built successfully.")
                return True, "Image built successfully"
            return False, res.stderr or res.stdout
        except Exception as e:
            return False, str(e)

    async def run(
        self,
        workspace_dir: str,
        request: ExecutionRequest
    ) -> ExecutionResult:
        """
        Executes pytest inside an isolated Docker container mounting ONLY the prepared candidate workspace.
        """
        patch_label: Literal["A", "B"] = request.patch
        session_id = request.session_id

        # 1. Verify Docker availability
        if not self.is_docker_available():
            logger.warning("DOCKER STATUS: NOT AVAILABLE. Docker executable is not installed or daemon is not accessible.")
            return ExecutionResult(
                patch=patch_label,
                status="error",
                stdout="",
                stderr="DOCKER STATUS: NOT AVAILABLE. Docker executable is not installed or the Docker daemon is not accessible.",
                exit_code=127,
                tests_passed=0,
                tests_failed=0,
                duration_ms=0,
                execution_mode="docker"
            )

        # 2. Validate test command
        is_cmd_valid, test_cmd = validate_test_command(request.test_command)
        if not is_cmd_valid:
            return ExecutionResult(
                patch=patch_label,
                status="error",
                stdout="",
                stderr=f"SECURITY_VIOLATION: {test_cmd}",
                exit_code=126,
                tests_passed=0,
                tests_failed=0,
                duration_ms=0,
                execution_mode="docker"
            )

        # 3. Ensure sandbox image exists
        if not self.is_image_available():
            built, build_err = self.build_sandbox_image()
            if not built:
                return ExecutionResult(
                    patch=patch_label,
                    status="error",
                    stdout="",
                    stderr=f"DOCKER_IMAGE_BUILD_ERROR: {build_err}",
                    exit_code=125,
                    tests_passed=0,
                    tests_failed=0,
                    duration_ms=0,
                    execution_mode="docker"
                )

        # 4. Formulate isolated container execution command
        container_name = f"swarm_box_{session_id[-8:]}_{patch_label}_{uuid.uuid4().hex[:6]}"
        abs_workspace = os.path.abspath(workspace_dir)

        # Build command args
        # Mount only the candidate workspace at /sandbox/repo
        cmd_args = [
            "docker", "run",
            "--name", container_name,
            "--rm",
            "--network", "none",
            "--memory", f"{self.limits.max_memory_mb}m",
            "--cpus", str(self.limits.cpu_limit),
            "--pids-limit", str(self.limits.pids_limit),
            "-v", f"{abs_workspace}:/sandbox/repo:rw",
            "-w", "/sandbox/repo",
            self.image,
            "sh", "-c", test_cmd
        ]

        logger.info(
            f"[DOCKER RUNNER] Dispatching Patch {patch_label} into isolated container '{container_name}' "
            f"(mem={self.limits.max_memory_mb}m, cpu={self.limits.cpu_limit}, net=none, timeout={self.limits.timeout_seconds}s)"
        )

        start_time = time.perf_counter()
        proc = None
        stdout = ""
        stderr = ""
        exit_code = 1
        status: Literal["passed", "failed", "error", "timeout"] = "failed"

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(self.limits.timeout_seconds)
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = proc.returncode or 0

            if exit_code == 0:
                status = "passed"
            elif exit_code in (125, 126, 127):
                status = "error"
            else:
                status = "failed"

        except asyncio.TimeoutError:
            logger.warning(f"Container '{container_name}' timed out after {self.limits.timeout_seconds}s. Terminating container...")
            status = "timeout"
            exit_code = 124
            stderr = f"TIMEOUT: Execution exceeded maximum timeout limit of {self.limits.timeout_seconds} seconds"
            # Explicitly force remove container
            try:
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=5)
            except Exception:
                pass

        except Exception as ex:
            logger.error(f"Error executing Docker container: {ex}")
            status = "error"
            exit_code = 1
            stderr = f"DOCKER_EXECUTION_EXCEPTION: {str(ex)}"

        finally:
            # Cleanup safeguard: ensure container is removed even if error occurred
            try:
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=5)
            except Exception:
                pass

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        tests_passed, tests_failed = PytestOutputParser.parse(stdout, stderr, exit_code)

        return ExecutionResult(
            patch=patch_label,
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            duration_ms=elapsed_ms,
            execution_mode="docker"
        )


# Alias for backward compatibility
DockerRunner = DockerSandboxRunner
