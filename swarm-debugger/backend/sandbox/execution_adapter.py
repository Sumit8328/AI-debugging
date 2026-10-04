import os
import shutil
import logging
import time
from typing import Optional, Literal

from backend.config import settings
from backend.schemas.execution import ExecutionResult, ExecutionRequest
from backend.sandbox.patch_validator import PatchSafetyValidator
from backend.sandbox.docker_runner import DockerSandboxRunner, DockerRunner

logger = logging.getLogger(__name__)

# Base root for the project workspace directory
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)


class ExecutionAdapter:
    """
    Unified Execution Adapter for SWARM DEBUGGER.

    Architecture Flow:
    Judge
      ↑
    Evidence
      ↑
    ExecutionAdapter
      ↑
    DockerRunner

    Responsibilities:
    1. Validates candidate patch security before any execution.
    2. Builds separate, isolated temporary workspaces for Patch A and Patch B.
    3. Applies the candidate patch to the isolated workspace.
    4. Dispatches the workspace to DockerRunner for containerized pytest execution.
    5. Cleans up the temporary workspace after execution proofs are captured.
    6. Ensures AI patches NEVER execute directly on the host machine.
    """

    def __init__(
        self,
        runner: Optional[DockerSandboxRunner] = None,
        allow_fallback: bool = False
    ):
        self.runner = runner or DockerSandboxRunner()
        self.allow_fallback = allow_fallback

    @property
    def is_docker(self) -> bool:
        """Returns True if the Docker runner has an accessible Docker daemon."""
        return self.runner.is_docker_available()

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Executes candidate patch within an isolated temporary workspace and Docker sandbox.
        """
        patch_label = request.patch
        session_id = request.session_id
        round_number = request.round_number

        # 1. Enforce static safety validation
        is_safe, error_msg = PatchSafetyValidator.validate_patch(request.patch_content)
        if not is_safe:
            logger.warning(f"Patch {patch_label} rejected by PatchSafetyValidator: {error_msg}")
            return ExecutionResult(
                patch=patch_label,
                status="error",
                stdout="[PATCH SAFETY VALIDATOR] Security check rejected candidate patch.",
                stderr=f"SECURITY_VIOLATION: {error_msg}",
                exit_code=126,
                tests_passed=0,
                tests_failed=0,
                duration_ms=5,
                execution_mode="docker"
            )

        # 2. Resolve original repository source path
        base_repo_path = self._resolve_repository_path(request.repository_path)
        if not os.path.exists(base_repo_path):
            return ExecutionResult(
                patch=patch_label,
                status="error",
                stdout="",
                stderr=f"REPOSITORY_NOT_FOUND: Base repository path '{base_repo_path}' does not exist.",
                exit_code=1,
                tests_passed=0,
                tests_failed=0,
                duration_ms=0,
                execution_mode="docker"
            )

        # 3. Create completely separate temporary workspace
        # Never execute Patch A and Patch B inside the same modified workspace.
        role_dir = "prosecutor" if patch_label == "A" else "defender"
        workspace_dir = os.path.join(
            PROJECT_ROOT,
            "workspace",
            session_id,
            f"round-{round_number}",
            role_dir
        )

        try:
            self._prepare_isolated_workspace(base_repo_path, workspace_dir)

            # 4. Apply candidate patch safely in the temporary workspace
            applied, apply_err = PatchSafetyValidator.apply_patch(workspace_dir, request.patch_content)
            if not applied:
                logger.warning(f"Failed to apply Patch {patch_label} in workspace: {apply_err}")
                return ExecutionResult(
                    patch=patch_label,
                    status="error",
                    stdout=f"[PATCH APPLIER] Could not apply candidate patch to workspace.",
                    stderr=f"PATCH_APPLICATION_ERROR: {apply_err}",
                    exit_code=1,
                    tests_passed=0,
                    tests_failed=0,
                    duration_ms=10,
                    execution_mode="docker"
                )

            # 5. Dispatch execution to DockerRunner
            if self.runner.is_docker_available():
                logger.info(f"Dispatching Patch {patch_label} to real Docker sandbox...")
                result = await self.runner.run(workspace_dir=workspace_dir, request=request)
                return result
            else:
                # Docker is not available
                if self.allow_fallback:
                    logger.warning("Docker unavailable; using deterministic demo execution adapter fallback")
                    return await DemoExecutionAdapter.run_patch_tests(
                        patch=request.patch_content,
                        patch_label=patch_label,
                        test_command=request.test_command,
                        round_number=round_number,
                        repo_path=workspace_dir
                    )
                else:
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

        finally:
            # 6. Cleanup temporary workspace when safe
            self._cleanup_workspace(workspace_dir)

    def _resolve_repository_path(self, raw_path: str) -> str:
        """Resolves demo-project IDs or filesystem paths to absolute paths."""
        if not raw_path or raw_path in ("mock-simulation", "default", "none"):
            return os.path.join(PROJECT_ROOT, "demo-projects", "bug-01")
        if os.path.isabs(raw_path) and os.path.exists(raw_path):
            return raw_path
        # Check relative to PROJECT_ROOT
        candidate = os.path.join(PROJECT_ROOT, raw_path)
        if os.path.exists(candidate):
            return candidate
        # Check inside demo-projects/
        candidate_demo = os.path.join(PROJECT_ROOT, "demo-projects", raw_path)
        if os.path.exists(candidate_demo):
            return candidate_demo
        # Default fallback to bug-01
        default_demo = os.path.join(PROJECT_ROOT, "demo-projects", "bug-01")
        if os.path.exists(default_demo):
            return default_demo
        return candidate

    def _prepare_isolated_workspace(self, base_repo_path: str, target_workspace_dir: str):
        """Copies original repository into fresh temporary workspace."""
        if os.path.exists(target_workspace_dir):
            shutil.rmtree(target_workspace_dir, ignore_errors=True)
        os.makedirs(target_workspace_dir, exist_ok=True)

        for root, dirs, files in os.walk(base_repo_path):
            # Ignore git and cache folders
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache", ".venv", "venv", "node_modules")]
            rel_dir = os.path.relpath(root, base_repo_path)
            dest_dir = os.path.join(target_workspace_dir, rel_dir) if rel_dir != "." else target_workspace_dir
            os.makedirs(dest_dir, exist_ok=True)
            for f in files:
                if not f.endswith((".pyc", ".pyo")):
                    shutil.copy2(os.path.join(root, f), os.path.join(dest_dir, f))

    def _cleanup_workspace(self, target_workspace_dir: str):
        """Safely cleans up temporary workspace."""
        try:
            if os.path.exists(target_workspace_dir):
                shutil.rmtree(target_workspace_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Could not remove temporary workspace {target_workspace_dir}: {e}")


class DemoExecutionAdapter:
    """
    Deterministic test simulation adapter (DEMO EXECUTION).
    Used as an explicit fallback when Docker is unavailable or mock simulation is active.
    Outputs are clearly marked as [DEMO EXECUTION].
    """

    @classmethod
    async def run_patch_tests(
        cls,
        patch: str,
        patch_label: str,  # "A" or "B"
        test_command: str = "pytest",
        round_number: int = 1,
        repo_path: Optional[str] = None
    ) -> ExecutionResult:
        normalized_label: Literal["A", "B"] = "B" if "B" in str(patch_label).upper() else "A"
        start = time.perf_counter()

        is_safe, error_msg = PatchSafetyValidator.validate_patch(patch)
        if not is_safe:
            return ExecutionResult(
                patch=normalized_label,
                status="error",
                stdout="[DEMO EXECUTION] Static security policy blocked patch.",
                stderr=f"SECURITY_VIOLATION: {error_msg}",
                exit_code=126,
                tests_passed=0,
                tests_failed=0,
                duration_ms=10,
                execution_mode="demo"
            )

        logger.info(
            f"[DEMO EXECUTION] Executing Patch {normalized_label} tests "
            f"via command: '{test_command}' (Round {round_number})"
        )

        if normalized_label == "B":
            # Fix B (Defender) handles edge cases and passes all tests
            stdout = (
                "[DEMO EXECUTION]\n"
                "============================= test session starts ==============================\n"
                "platform linux -- Python 3.12.2, pytest-8.1.1, pluggy-1.4.0\n"
                "rootdir: /sandbox/repo\n"
                "collected 5 items\n\n"
                "test_processor.py::test_standard_batch PASSED                             [ 20%]\n"
                "test_processor.py::test_boundary_exact_match PASSED                       [ 40%]\n"
                "test_processor.py::test_empty_input PASSED                                [ 60%]\n"
                "test_processor.py::test_single_item PASSED                                [ 80%]\n"
                "test_processor.py::test_zero_or_negative_batch_size PASSED                [100%]\n\n"
                "============================== 5 passed in 0.42s ==============================="
            )
            stderr = ""
            status = "passed"
            exit_code = 0
            tests_passed = 5
            tests_failed = 0
            base_ms = 412
        else:
            # Fix A (Prosecutor) fixes primary test but fails zero/negative batch size regression
            stdout = (
                "[DEMO EXECUTION]\n"
                "============================= test session starts ==============================\n"
                "platform linux -- Python 3.12.2, pytest-8.1.1, pluggy-1.4.0\n"
                "rootdir: /sandbox/repo\n"
                "collected 5 items\n\n"
                "test_processor.py::test_standard_batch PASSED                             [ 20%]\n"
                "test_processor.py::test_boundary_exact_match PASSED                       [ 40%]\n"
                "test_processor.py::test_empty_input PASSED                                [ 60%]\n"
                "test_processor.py::test_single_item PASSED                                [ 80%]\n"
                "test_processor.py::test_zero_or_negative_batch_size FAILED                [100%]\n\n"
                "=================================== FAILURES ===================================\n"
                "______________________ test_zero_or_negative_batch_size ________________________\n"
                "    def test_zero_or_negative_batch_size():\n"
                "        with pytest.raises(ValueError):\n"
                ">           slice_batch([1, 2, 3], batch_size=0)\n"
                "E           Failed: DID NOT RAISE <class 'ValueError'>\n"
                "test_processor.py:28: Failed\n"
                "=========================== 1 failed, 4 passed in 0.38s ==========================="
            )
            stderr = "FAILED test_processor.py::test_zero_or_negative_batch_size - Failed: DID NOT RAISE <class 'ValueError'>"
            status = "failed"
            exit_code = 1
            tests_passed = 4
            tests_failed = 1
            base_ms = 385

        elapsed = int((time.perf_counter() - start) * 1000) + base_ms

        return ExecutionResult(
            patch=normalized_label,
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            duration_ms=elapsed,
            execution_mode="demo"
        )
