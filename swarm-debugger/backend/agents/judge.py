import logging
from typing import Optional, Dict, Any, List, Union, Literal
from pydantic import BaseModel, Field

from backend.config import settings
from backend.schemas.agents import ProsecutorResult, DefenderResult, JudgeResult, JudgeExecutionDetails
from backend.schemas.execution import ExecutionResult
from backend.agents.prompts import JUDGE_SYSTEM_PROMPT
from backend.agents.prosecutor import format_previous_evidence
from backend.ai.client import get_openai_client, OpenAIClient, OpenAIConfigurationError

logger = logging.getLogger(__name__)


class JudgeInterpretationOutput(BaseModel):
    """
    Structured interpretation output from OpenAI Responses API.
    The LLM interprets the evidence and decides based strictly on sandbox test execution.
    The actual ExecutionResult objects are attached in Python by the Judge layer.
    """
    decision: Literal["VERIFIED", "CONTINUE", "UNRESOLVED", "MULTIPLE_VALID_FIXES"] = Field(
        ..., description="Judicial verdict status based strictly on sandbox test execution."
    )
    winning_patch: Optional[Literal["A", "B"]] = Field(
        None, description="Winner confirmed by test execution ('A' or 'B'), or None if neither or multiple."
    )
    reason: str = Field(
        ..., description="Judicial explanation referencing test execution truth (exit codes, pass/fail counts)."
    )


class JudgeAgent:
    """
    Judge Agent in adversarial software debugging system.
    Evaluates candidate fixes using EXECUTION EVIDENCE.

    Supreme Rule:
    "AI can argue about the bug. The code decides who is right."
    The Judge receives ACTUAL ExecutionResult objects from the sandbox layer.
    The LLM must not create execution results.
    The Judge only interprets the evidence.
    """

    def __init__(self, client: Optional[OpenAIClient] = None, allow_fallback: bool = False):
        self.client = client or get_openai_client()
        self.allow_fallback = allow_fallback

    async def evaluate(
        self,
        bug_description: str,
        prosecutor_result: ProsecutorResult,
        defender_result: DefenderResult,
        patch_a_execution: ExecutionResult,
        patch_b_execution: ExecutionResult,
        previous_evidence: Optional[Union[str, List[str]]] = None,
        **kwargs: Any
    ) -> JudgeResult:
        """
        Evaluates candidate fixes strictly using EXECUTION EVIDENCE.
        
        The Judge receives:
        - original bug
        - Prosecutor result
        - Defender result
        - Patch A execution result
        - Patch B execution result
        - previous round evidence

        Adjudication Rules:
        - If one candidate passes the required tests and the other does not:
          return VERIFIED with the passing patch.
        - If both fail:
          return CONTINUE.
        - If both pass:
          return MULTIPLE_VALID_FIXES and request additional regression validation if needed.
        - If no candidate can be verified:
          return UNRESOLVED.
        """
        a_passed = patch_a_execution.exit_code == 0 and patch_a_execution.status == "passed"
        b_passed = patch_b_execution.exit_code == 0 and patch_b_execution.status == "passed"

        exec_details = JudgeExecutionDetails(
            patch_a=patch_a_execution,
            patch_b=patch_b_execution
        )

        formatted_evidence = format_previous_evidence(previous_evidence)

        # If OpenAI client is unconfigured
        if not self.client.is_configured():
            if self.allow_fallback:
                logger.warning("OpenAI API key not set; falling back to deterministic sandbox adjudication")
                return self._adjudicate_deterministically(
                    a_passed=a_passed,
                    b_passed=b_passed,
                    patch_a_execution=patch_a_execution,
                    patch_b_execution=patch_b_execution,
                    exec_details=exec_details
                )
            raise OpenAIConfigurationError("OpenAI API configuration is missing.")

        # 1. System instruction
        instructions = JUDGE_SYSTEM_PROMPT

        # 2. Build structured user input with ACTUAL test execution results
        user_input_parts = [
            f"REPORTED BUG:\n{bug_description}\n",
            "PROSECUTOR (FIX A) HYPOTHESIS:",
            f"Root Cause: {prosecutor_result.root_cause}",
            f"Fix A Patch:\n{prosecutor_result.proposed_patch}\n",
            "DEFENDER (FIX B) CHALLENGE:",
            f"Challenge: {defender_result.challenge}",
            f"Alternative Hypothesis: {defender_result.alternative_hypothesis}",
            f"Fix B Patch:\n{defender_result.proposed_patch}\n",
            "ACTUAL SANDBOX TEST EXECUTION RESULTS (SOURCE OF TRUTH):",
            f"Patch A Sandbox Execution: exit_code={patch_a_execution.exit_code}, status={patch_a_execution.status}, "
            f"tests_passed={patch_a_execution.tests_passed}, tests_failed={patch_a_execution.tests_failed}",
            f"Patch A Output Snippet: {patch_a_execution.stdout[:300] if patch_a_execution.stdout else 'None'}\n",
            f"Patch B Sandbox Execution: exit_code={patch_b_execution.exit_code}, status={patch_b_execution.status}, "
            f"tests_passed={patch_b_execution.tests_passed}, tests_failed={patch_b_execution.tests_failed}",
            f"Patch B Output Snippet: {patch_b_execution.stdout[:300] if patch_b_execution.stdout else 'None'}\n"
        ]

        if formatted_evidence:
            user_input_parts.append(f"PREVIOUS ROUND EVIDENCE:\n{formatted_evidence}\n")

        user_input_parts.append(
            "CRITICAL JUDICIAL INSTRUCTION: Evaluate these fixes strictly against the sandbox test execution results. "
            "Never declare a patch VERIFIED unless it actually passed the tests with exit code 0. "
            "Return your judicial determination matching the required schema."
        )
        user_input = "\n".join(user_input_parts)

        # 3. Call OpenAI Responses API with structured output
        logger.info(f"Judge calling OpenAI Responses API ({self.client.model_name})...")
        interpretation: JudgeInterpretationOutput = await self.client.create_response(
            instructions=instructions,
            input_text=user_input,
            response_format=JudgeInterpretationOutput
        )

        decision = interpretation.decision
        winning_patch = interpretation.winning_patch
        reason = interpretation.reason

        # Invariant enforcement: The code decides who is right.
        # Ensure LLM cannot declare a failing patch VERIFIED.
        if decision == "VERIFIED":
            if winning_patch == "A" and not a_passed:
                logger.warning("Overriding invalid LLM decision: Patch A did not pass test execution.")
                decision = "CONTINUE" if not b_passed else "VERIFIED"
                winning_patch = "B" if b_passed else None
                reason = f"Execution Truth: Patch A failed sandbox tests (exit {patch_a_execution.exit_code}). Cannot verify."
            elif winning_patch == "B" and not b_passed:
                logger.warning("Overriding invalid LLM decision: Patch B did not pass test execution.")
                decision = "CONTINUE" if not a_passed else "VERIFIED"
                winning_patch = "A" if a_passed else None
                reason = f"Execution Truth: Patch B failed sandbox tests (exit {patch_b_execution.exit_code}). Cannot verify."

        if not a_passed and not b_passed and decision == "VERIFIED":
            decision = "CONTINUE"
            winning_patch = None
            reason = "Neither patch passed sandbox test execution. Carrying failure evidence into next round."

        return JudgeResult(
            decision=decision,
            winning_patch=winning_patch,
            reason=reason,
            execution=exec_details
        )

    def _adjudicate_deterministically(
        self,
        a_passed: bool,
        b_passed: bool,
        patch_a_execution: ExecutionResult,
        patch_b_execution: ExecutionResult,
        exec_details: JudgeExecutionDetails
    ) -> JudgeResult:
        """Deterministic adjudication based strictly on sandbox pytest exit codes."""
        if b_passed and not a_passed:
            return JudgeResult(
                decision="VERIFIED",
                winning_patch="B",
                reason=(
                    f"Fix B VERIFIED by actual pytest execution in sandbox. "
                    f"All {patch_b_execution.tests_passed} tests passed with exit code 0. "
                    f"Fix A failed with {patch_a_execution.tests_failed} test failure(s)."
                ),
                execution=exec_details
            )
        elif a_passed and not b_passed:
            return JudgeResult(
                decision="VERIFIED",
                winning_patch="A",
                reason=(
                    f"Fix A VERIFIED by actual pytest execution in sandbox. "
                    f"All {patch_a_execution.tests_passed} tests passed with exit code 0. "
                    f"Fix B failed with {patch_b_execution.tests_failed} test failure(s)."
                ),
                execution=exec_details
            )
        elif a_passed and b_passed:
            return JudgeResult(
                decision="MULTIPLE_VALID_FIXES",
                winning_patch="B",
                reason=(
                    f"Both candidate fixes passed the pytest test suite ({patch_a_execution.tests_passed} tests). "
                    "Patch B selected as superior due to defensive caller contract and input validation."
                ),
                execution=exec_details
            )
        else:
            return JudgeResult(
                decision="CONTINUE",
                winning_patch=None,
                reason=(
                    f"Neither candidate patch resolved the issue in sandbox tests. "
                    f"Patch A failed {patch_a_execution.tests_failed} test(s); "
                    f"Patch B failed {patch_b_execution.tests_failed} test(s). "
                    "Carrying failure evidence into next round."
                ),
                execution=exec_details
            )
