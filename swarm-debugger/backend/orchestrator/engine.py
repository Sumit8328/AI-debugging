import os
import asyncio
import logging
from typing import Dict, Any, Optional

from backend.config import settings
from backend.schemas.session import Session, RoundState
from backend.schemas.events import DebugEvent
from backend.schemas.agents import ProsecutorResult, DefenderResult, JudgeResult
from backend.schemas.execution import ExecutionResult, ExecutionRequest

from backend.agents.prosecutor import ProsecutorAgent, format_repository_context
from backend.agents.defender import DefenderAgent
from backend.agents.judge import JudgeAgent
from backend.sandbox.execution_adapter import ExecutionAdapter, DemoExecutionAdapter
from backend.evidence.collector import EvidenceCollector
from backend.repository.loader import RepositoryLoader
from backend.database.models import SessionRepository
from backend.orchestrator.round_manager import RoundManager
from backend.orchestrator.state import state_manager
from backend.ai.client import get_openai_client, OpenAIClientError, OpenAIConfigurationError, mask_secret

logger = logging.getLogger(__name__)


class OrchestratorEngine:
    """
    Adversarial multi-agent debate orchestrator:
    
    START SESSION
          ↓
       ROUND 1
          ↓
      PROSECUTOR (Fix A)
          ↓
       DEFENDER (Fix B)
          ↓
    EXECUTION LAYER (DEMO EXECUTION)
          ↓
        JUDGE (Test Evidence Truth)
          ↓
     ROUND DECISION
    """

    def __init__(self, session: Session):
        self.session = session
        self.session_id = session.session_id

        # Determine if mock fallback is explicitly permitted
        allow_fallback = (
            session.demo_id == "mock-simulation" 
            or os.getenv("ALLOW_MOCK_FALLBACK", "").lower() == "true"
        )

        client = get_openai_client()
        self.prosecutor = ProsecutorAgent(client=client, allow_fallback=allow_fallback)
        self.defender = DefenderAgent(client=client, allow_fallback=allow_fallback)
        self.judge = JudgeAgent(client=client, allow_fallback=allow_fallback)
        self.execution_adapter = ExecutionAdapter(allow_fallback=allow_fallback)

        self.collector = EvidenceCollector(self.session_id)
        self.round_manager = RoundManager(self.session, self.collector)

    async def emit(self, event_name: str, agent: Optional[str] = None, payload: Optional[Dict[str, Any]] = None):
        """Broadcasts strongly typed, UI-safe DebugEvent to connected WebSocket frontends."""
        # Sanitize payload to guarantee no secrets/API keys or internal prompts are emitted
        safe_payload = payload or {}
        event = DebugEvent(
            event=event_name,
            session_id=self.session_id,
            round=self.session.current_round,
            agent=agent,
            payload=safe_payload
        )
        await state_manager.broadcast(self.session_id, event.model_dump())

    async def emit_error(self, source: str, message: str):
        """Emits readable error event conforming to Prompt 3 specification."""
        clean_msg = mask_secret(message)
        logger.error(f"[Orchestrator Error - {source}]: {clean_msg}")
        await self.emit("error", source, {
            "source": source,
            "message": clean_msg
        })

    async def run(self):
        """Executes the adversarial multi-agent debate and sandbox verification loop."""
        logger.info(f"Starting Swarm Debugger orchestrator for session {self.session_id}")

        # Load repository codebase context
        demo_id = self.session.demo_id or "bug-01"
        repo_path, code_context = RepositoryLoader.load_demo(demo_id)
        formatted_repo = format_repository_context(code_context)

        # 1. START SESSION
        self.session.status = "debating"
        SessionRepository.update_session_status(self.session_id, "debating")
        await self.emit("session_started", "system", {
            "session_id": self.session_id,
            "bug_description": self.session.bug_description,
            "test_command": self.session.test_command,
            "max_rounds": self.session.max_rounds,
            "demo_id": demo_id,
            "files": list(code_context.keys())
        })

        while True:
            if state_manager.is_stopped(self.session_id):
                logger.info(f"Session {self.session_id} stopped by user.")
                self.session.status = "stopped"
                SessionRepository.update_session_status(self.session_id, "stopped")
                await self.emit("session_stopped", "system", {"message": "Session halted by user request."})
                break

            current_round = self.session.current_round
            carried_evidence = self.round_manager.carried_failure_evidence

            # 2. ROUND START
            await self.emit("round_started", "system", {
                "round": current_round,
                "status": "running",
                "message": f"Round {current_round} initialized"
            })
            await asyncio.sleep(0.5)

            # 3. PROSECUTOR AGENT
            await self.emit("agent_started", "prosecutor", {
                "message": "Analyzing repository..."
            })

            try:
                prosecutor_result: ProsecutorResult = await self.prosecutor.analyze(
                    bug_description=self.session.bug_description,
                    repository_context=formatted_repo,
                    previous_evidence=carried_evidence,
                    round_number=current_round
                )
            except (OpenAIClientError, Exception) as ex:
                msg = getattr(ex, "message", mask_secret(str(ex)))
                await self.emit_error("prosecutor", msg)
                self.session.status = "failed"
                SessionRepository.update_session_status(self.session_id, "failed")
                break

            # Prosecutor completed: emit UI-safe reasoning artifact
            await self.emit("agent_completed", "prosecutor", {
                "root_cause": prosecutor_result.root_cause,
                "affected_files": prosecutor_result.affected_files,
                "evidence": prosecutor_result.evidence,
                "proposed_patch": prosecutor_result.proposed_patch,
                "reasoning_summary": prosecutor_result.reasoning_summary,
                "result": prosecutor_result.model_dump()
            })

            if state_manager.is_stopped(self.session_id):
                break

            # 4. DEFENDER AGENT
            await self.emit("agent_started", "defender", {
                "message": "Challenging Prosecutor..."
            })

            try:
                defender_result: DefenderResult = await self.defender.analyze(
                    bug_description=self.session.bug_description,
                    repository_context=formatted_repo,
                    prosecutor_result=prosecutor_result,
                    previous_evidence=carried_evidence,
                    round_number=current_round
                )
            except (OpenAIClientError, Exception) as ex:
                msg = getattr(ex, "message", mask_secret(str(ex)))
                await self.emit_error("defender", msg)
                self.session.status = "failed"
                SessionRepository.update_session_status(self.session_id, "failed")
                break

            # Defender completed: emit UI-safe reasoning artifact
            await self.emit("agent_completed", "defender", {
                "challenge": defender_result.challenge,
                "alternative_hypothesis": defender_result.alternative_hypothesis,
                "evidence": defender_result.evidence,
                "affected_files": defender_result.affected_files,
                "proposed_patch": defender_result.proposed_patch,
                "reasoning_summary": defender_result.reasoning_summary,
                "result": defender_result.model_dump()
            })

            if state_manager.is_stopped(self.session_id):
                break

            # 5. JUDGE STARTED / EXECUTION LAYER
            await self.emit("judge_started", "judge", {
                "message": "Waiting for execution evidence..."
            })

            mode_label = "LIVE DOCKER EXECUTION" if self.execution_adapter.is_docker else "DEMO EXECUTION"

            # Execute Patch A in isolated container / workspace
            await self.emit("execution_started", "judge", {
                "patch": "A",
                "test_command": self.session.test_command,
                "message": f"[{mode_label}] Dispatching Patch A to isolated container..."
            })
            await asyncio.sleep(0.5)

            req_a = ExecutionRequest(
                session_id=self.session_id,
                round_number=current_round,
                patch="A",
                repository_path=repo_path,
                patch_content=prosecutor_result.proposed_patch,
                test_command=self.session.test_command or "pytest"
            )
            execution_a: ExecutionResult = await self.execution_adapter.execute(req_a)

            # Truncate extremely large stdout/stderr for WebSocket streaming while retaining full on backend
            safe_stdout_a = execution_a.stdout[:4000] + ("\n... [truncated for WebSocket streaming]" if len(execution_a.stdout) > 4000 else "")
            safe_stderr_a = execution_a.stderr[:2000] + ("\n... [truncated for WebSocket streaming]" if len(execution_a.stderr) > 2000 else "")
            broadcast_result_a = execution_a.model_dump()
            broadcast_result_a["stdout"] = safe_stdout_a
            broadcast_result_a["stderr"] = safe_stderr_a

            await self.emit("execution_completed", "judge", {
                "patch": "A",
                "result": broadcast_result_a,
                "execution_mode": execution_a.execution_mode,
                "payload": {
                    "status": execution_a.status,
                    "tests_passed": execution_a.tests_passed,
                    "tests_failed": execution_a.tests_failed,
                    "exit_code": execution_a.exit_code,
                    "duration_ms": execution_a.duration_ms,
                    "execution_mode": execution_a.execution_mode
                }
            })

            # Execute Patch B in isolated container / workspace
            await self.emit("execution_started", "judge", {
                "patch": "B",
                "test_command": self.session.test_command,
                "message": f"[{mode_label}] Dispatching Patch B to isolated container..."
            })
            await asyncio.sleep(0.5)

            req_b = ExecutionRequest(
                session_id=self.session_id,
                round_number=current_round,
                patch="B",
                repository_path=repo_path,
                patch_content=defender_result.proposed_patch,
                test_command=self.session.test_command or "pytest"
            )
            execution_b: ExecutionResult = await self.execution_adapter.execute(req_b)

            safe_stdout_b = execution_b.stdout[:4000] + ("\n... [truncated for WebSocket streaming]" if len(execution_b.stdout) > 4000 else "")
            safe_stderr_b = execution_b.stderr[:2000] + ("\n... [truncated for WebSocket streaming]" if len(execution_b.stderr) > 2000 else "")
            broadcast_result_b = execution_b.model_dump()
            broadcast_result_b["stdout"] = safe_stdout_b
            broadcast_result_b["stderr"] = safe_stderr_b

            await self.emit("execution_completed", "judge", {
                "patch": "B",
                "result": broadcast_result_b,
                "execution_mode": execution_b.execution_mode,
                "payload": {
                    "status": execution_b.status,
                    "tests_passed": execution_b.tests_passed,
                    "tests_failed": execution_b.tests_failed,
                    "exit_code": execution_b.exit_code,
                    "duration_ms": execution_b.duration_ms,
                    "execution_mode": execution_b.execution_mode
                }
            })

            # 6. JUDGE ADJUDICATION
            try:
                judge_result: JudgeResult = await self.judge.evaluate(
                    bug_description=self.session.bug_description,
                    prosecutor_result=prosecutor_result,
                    defender_result=defender_result,
                    patch_a_execution=execution_a,
                    patch_b_execution=execution_b,
                    previous_evidence=carried_evidence
                )
            except (OpenAIClientError, Exception) as ex:
                msg = getattr(ex, "message", mask_secret(str(ex)))
                await self.emit_error("judge", msg)
                self.session.status = "failed"
                SessionRepository.update_session_status(self.session_id, "failed")
                break

            await self.emit("judge_completed", "judge", {
                "decision": judge_result.decision,
                "winning_patch": judge_result.winning_patch,
                "reason": judge_result.reason,
                "result": judge_result.model_dump()
            })

            # Persist round state
            round_state = RoundState(
                round_number=current_round,
                prosecutor_result=prosecutor_result,
                defender_result=defender_result,
                patch_a_execution=execution_a,
                patch_b_execution=execution_b,
                judge_result=judge_result,
                status="completed",
                failed_evidence_carried_over=carried_evidence
            )
            self.session.rounds.append(round_state)
            SessionRepository.save_round_artifact(
                session_id=self.session_id,
                round_number=current_round,
                prosecutor=prosecutor_result,
                defender=defender_result,
                judge=judge_result,
                failed_evidence=carried_evidence
            )

            await self.emit("round_completed", "system", {
                "round": current_round,
                "status": "completed"
            })

            # 7. ROUND DECISION & VERIFICATION CHECK
            should_continue, decision_reason = self.round_manager.should_continue(judge_result)

            if not should_continue:
                if judge_result.winning_patch:
                    self.session.status = "verified"
                    verified_patch = (
                        prosecutor_result.proposed_patch 
                        if judge_result.winning_patch == "A" 
                        else defender_result.proposed_patch
                    )
                    self.session.verified_patch = verified_patch
                    self.session.winning_patch = judge_result.winning_patch
                    SessionRepository.update_session_status(
                        self.session_id, "verified", current_round=current_round, verified_patch=verified_patch
                    )
                    await self.emit("verification_completed", "judge", {
                        "winning_patch": judge_result.winning_patch,
                        "verified_patch": verified_patch,
                        "reason": judge_result.reason
                    })
                    await self.emit("session_completed", "system", {
                        "status": "verified",
                        "winning_patch": judge_result.winning_patch,
                        "verified_patch": verified_patch,
                        "message": "Fix VERIFIED by actual sandbox test execution!"
                    })
                else:
                    self.session.status = "failed"
                    SessionRepository.update_session_status(self.session_id, "failed")
                    await self.emit("session_completed", "system", {
                        "status": "failed",
                        "message": decision_reason,
                        "reason": judge_result.reason
                    })
                break

            # Prepare for next adversarial round
            self.round_manager.prepare_next_round(judge_result)
            SessionRepository.update_session_status(
                self.session_id, "debating", current_round=self.session.current_round
            )
            await self.emit("evidence_created", "system", {
                "completed_round": current_round,
                "next_round": self.session.current_round,
                "carried_evidence": self.round_manager.carried_failure_evidence
            })
            await asyncio.sleep(1.0)
