import os
import shutil
import asyncio
import pytest
from unittest.mock import patch, MagicMock

from backend.schemas.execution import ExecutionResult, ExecutionRequest
from backend.sandbox.patch_validator import PatchSafetyValidator
from backend.sandbox.docker_runner import DockerSandboxRunner, PytestOutputParser, validate_test_command
from backend.sandbox.execution_adapter import ExecutionAdapter, DemoExecutionAdapter, PROJECT_ROOT


# 1. Test successful pytest output parsing and execution
def test_successful_pytest_execution():
    stdout_sample = (
        "============================= test session starts ==============================\n"
        "test_processor.py::test_standard_batch PASSED\n"
        "test_processor.py::test_boundary_exact_match PASSED\n"
        "test_processor.py::test_empty_input PASSED\n"
        "============================== 5 passed in 0.42s ==============================="
    )
    passed, failed = PytestOutputParser.parse(stdout_sample, "", 0)
    assert passed == 5
    assert failed == 0

    stdout_25 = "25 passed, 0 failed in 1.10s"
    passed_25, failed_25 = PytestOutputParser.parse(stdout_25, "", 0)
    assert passed_25 == 25
    assert failed_25 == 0


# 2. Test failing pytest output parsing and execution
def test_failing_pytest_execution():
    stdout_sample = (
        "=================================== FAILURES ===================================\n"
        "FAILED test_processor.py::test_zero_or_negative_batch_size - Failed: DID NOT RAISE\n"
        "=========================== 1 failed, 4 passed in 0.38s ==========================="
    )
    passed, failed = PytestOutputParser.parse(stdout_sample, "", 1)
    assert passed == 4
    assert failed == 1

    stdout_23 = "23 passed, 2 failed in 0.85s"
    passed_23, failed_23 = PytestOutputParser.parse(stdout_23, "", 1)
    assert passed_23 == 23
    assert failed_23 == 2


# 3. Test execution timeout handling
def test_execution_timeout():
    async def _run():
        runner = DockerSandboxRunner()
        req = ExecutionRequest(
            session_id="sess_test_timeout",
            round_number=1,
            patch="A",
            repository_path="demo-projects/bug-01",
            patch_content="--- a/processor.py\n+++ b/processor.py\n@@ -1 +1 @@\n-x\n+y"
        )

        mock_proc = MagicMock()
        with patch.object(runner, "is_docker_available", return_value=True), \
             patch.object(runner, "is_image_available", return_value=True), \
             patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            
            result = await runner.run("dummy_workspace", req)
            assert result.status == "timeout"
            assert result.exit_code == 124
            assert "TIMEOUT" in result.stderr

    asyncio.run(_run())


# 4. Test invalid patch rejection (static security validation)
def test_invalid_patch_security_rejection():
    # Dangerous subprocess pattern
    dangerous_patch = """--- a/processor.py
+++ b/processor.py
@@ -1,3 +1,4 @@
+import subprocess
+subprocess.run(["rm", "-rf", "/"])
"""
    is_safe, err = PatchSafetyValidator.validate_patch(dangerous_patch)
    assert not is_safe
    assert "restricted pattern" in err or "subprocess" in err

    # Path traversal pattern
    traversal_patch = """--- a/../../../etc/passwd
+++ b/../../../etc/passwd
@@ -1 +1 @@
-root
+hacked
"""
    is_safe_trav, err_trav = PatchSafetyValidator.validate_patch(traversal_patch)
    assert not is_safe_trav
    assert "Path traversal" in err_trav or "forbidden" in err_trav

    # Secret credential access pattern
    secret_patch = """--- a/processor.py
+++ b/processor.py
@@ -1 +1 @@
+with open('.env') as f: key = f.read()
"""
    is_safe_sec, err_sec = PatchSafetyValidator.validate_patch(secret_patch)
    assert not is_safe_sec
    assert "credential" in err_sec or "protected" in err_sec


def test_execution_adapter_rejects_dangerous_patch():
    async def _run():
        adapter = ExecutionAdapter()
        req = ExecutionRequest(
            session_id="sess_test_sec",
            round_number=1,
            patch="A",
            repository_path="demo-projects/bug-01",
            patch_content="import os; os.system('cat /etc/shadow')"
        )
        result = await adapter.execute(req)
        assert result.status == "error"
        assert result.exit_code == 126
        assert "SECURITY_VIOLATION" in result.stderr

    asyncio.run(_run())


# 5. Test patch isolation between candidate A and candidate B
def test_patch_isolation():
    base_repo = os.path.join(PROJECT_ROOT, "demo-projects", "bug-01")
    workspace_a = os.path.join(PROJECT_ROOT, "workspace", "test_isolation", "round-1", "prosecutor")
    workspace_b = os.path.join(PROJECT_ROOT, "workspace", "test_isolation", "round-1", "defender")

    adapter = ExecutionAdapter()
    try:
        adapter._prepare_isolated_workspace(base_repo, workspace_a)
        adapter._prepare_isolated_workspace(base_repo, workspace_b)

        patch_a = """--- a/processor.py
+++ b/processor.py
@@ -9,2 +9,2 @@
-    for i in range(0, len(items) + 1, batch_size):
+    for i in range(0, len(items), batch_size):
"""
        patch_b = """--- a/processor.py
+++ b/processor.py
@@ -1,2 +1,3 @@
 def slice_batch(items, batch_size):
+    # DEFENDER_INDEPENDENT_CHECK
"""
        applied_a, _ = PatchSafetyValidator.apply_patch(workspace_a, patch_a)
        applied_b, _ = PatchSafetyValidator.apply_patch(workspace_b, patch_b)

        assert applied_a
        assert applied_b

        with open(os.path.join(workspace_a, "processor.py"), "r", encoding="utf-8") as fa:
            content_a = fa.read()

        with open(os.path.join(workspace_b, "processor.py"), "r", encoding="utf-8") as fb:
            content_b = fb.read()

        with open(os.path.join(base_repo, "processor.py"), "r", encoding="utf-8") as f_orig:
            content_orig = f_orig.read()

        # Patch A must not be in Workspace B
        assert "DEFENDER_INDEPENDENT_CHECK" in content_b
        assert "DEFENDER_INDEPENDENT_CHECK" not in content_a

        # Original repo must remain unchanged
        assert "DEFENDER_INDEPENDENT_CHECK" not in content_orig
        assert "len(items) + 1" in content_orig

    finally:
        adapter._cleanup_workspace(os.path.join(PROJECT_ROOT, "workspace", "test_isolation"))


# 6. Test workspace cleanup
def test_workspace_cleanup():
    async def _run():
        adapter = ExecutionAdapter(allow_fallback=True)
        session_id = "sess_cleanup_test"
        workspace_dir = os.path.join(PROJECT_ROOT, "workspace", session_id)

        req = ExecutionRequest(
            session_id=session_id,
            round_number=1,
            patch="B",
            repository_path="demo-projects/bug-01",
            patch_content="""--- a/processor.py
+++ b/processor.py
@@ -9,2 +9,2 @@
-    for i in range(0, len(items) + 1, batch_size):
+    for i in range(0, len(items), batch_size):
"""
        )
        result = await adapter.execute(req)
        assert result.status in ("passed", "error")
        # Verify temporary candidate directory was cleaned up
        assert not os.path.exists(os.path.join(workspace_dir, "round-1", "defender"))

    asyncio.run(_run())


# 7. Test Docker availability detection and clean reporting
def test_docker_availability_detection():
    runner = DockerSandboxRunner()
    available = runner.is_docker_available()
    assert isinstance(available, bool)


# 8. Test command validation
def test_test_command_validation():
    ok, cmd = validate_test_command("pytest -q")
    assert ok
    assert cmd == "pytest -q"

    ok_py, cmd_py = validate_test_command("python -m pytest test_processor.py")
    assert ok_py

    bad, msg = validate_test_command("pytest; rm -rf /")
    assert not bad
    assert "Forbidden" in msg

    bad_node, msg_node = validate_test_command("npm test")
    assert not bad_node
    assert "Only 'pytest'" in msg_node
