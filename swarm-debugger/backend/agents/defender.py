import logging
from typing import Optional, Dict, Any, List, Union
from backend.config import settings
from backend.schemas.agents import ProsecutorResult, DefenderResult
from backend.agents.prompts import DEFENDER_SYSTEM_PROMPT
from backend.agents.prosecutor import format_repository_context, format_previous_evidence
from backend.ai.client import get_openai_client, OpenAIClient, OpenAIConfigurationError

logger = logging.getLogger(__name__)


class DefenderAgent:
    """
    Defender Agent in adversarial software debugging system.
    Challenges the Prosecutor's hypothesis and proposes an alternative Fix B.
    Actively checks for incorrect assumptions, alternative root causes, edge cases,
    and possible regressions.
    """

    def __init__(self, client: Optional[OpenAIClient] = None, allow_fallback: bool = False):
        self.client = client or get_openai_client()
        self.allow_fallback = allow_fallback

    async def analyze(
        self,
        bug_description: str,
        repository_context: Union[str, Dict[str, str]],
        prosecutor_result: ProsecutorResult,
        previous_evidence: Optional[Union[str, List[str]]] = None,
        **kwargs: Any
    ) -> DefenderResult:
        """
        Challenges Prosecutor's hypothesis and proposes alternative Fix B.
        1. Build the Defender system prompt.
        2. Build structured user input containing:
           - bug description
           - repository context
           - Prosecutor result (Fix A, root cause, evidence)
           - previous evidence
           - explicit adversarial instruction
        3. Call OpenAI Responses API.
        4. Request structured output matching DefenderResult.
        5. Validate and return DefenderResult.
        """
        formatted_repo = format_repository_context(repository_context)
        formatted_evidence = format_previous_evidence(previous_evidence)

        # Check if OpenAI client is configured
        if not self.client.is_configured():
            if self.allow_fallback:
                logger.warning("OpenAI API key not set; falling back to deterministic mock artifact")
                round_num = kwargs.get("round_number", 1)
                return self._generate_mock_result(
                    bug_description, prosecutor_result, formatted_repo, round_num, formatted_evidence
                )
            raise OpenAIConfigurationError("OpenAI API configuration is missing.")

        # 1. System instruction
        instructions = DEFENDER_SYSTEM_PROMPT

        # 2. Build structured user input with Prosecutor's result and explicit adversarial challenge
        user_input_parts = [
            f"REPORTED BUG:\n{bug_description}\n",
            f"REPOSITORY CONTEXT:\n{formatted_repo}\n",
            "PROSECUTOR INDICTMENT & FIX A:",
            f"Root Cause: {prosecutor_result.root_cause}",
            f"Evidence: {', '.join(prosecutor_result.evidence)}",
            f"Affected Files: {', '.join(prosecutor_result.affected_files)}",
            f"Fix A Patch:\n{prosecutor_result.proposed_patch}",
            f"Prosecutor Reasoning: {prosecutor_result.reasoning_summary}\n"
        ]

        if formatted_evidence:
            user_input_parts.append(f"PREVIOUS ROUND EVIDENCE:\n{formatted_evidence}\n")

        user_input_parts.append(
            "MANDATORY INSTRUCTION: Do not agree with the Prosecutor unless you independently find the evidence convincing. "
            "Search for an alternative explanation. Inspect the code for hidden edge cases, input assumptions, or regressions that Fix A would cause. "
            "Formulate an independent Fix B."
        )
        user_input = "\n".join(user_input_parts)

        # 3. Call OpenAI Responses API with structured output
        logger.info(f"Defender calling OpenAI Responses API ({self.client.model_name})...")
        result = await self.client.create_response(
            instructions=instructions,
            input_text=user_input,
            response_format=DefenderResult
        )

        # 4 & 5. Validate output with DefenderResult
        validated: DefenderResult = DefenderResult.model_validate(result)
        logger.info(f"Defender generated validated challenge: {validated.challenge[:80]}...")
        return validated

    async def challenge_and_propose(
        self,
        bug_description: str,
        prosecutor_result: ProsecutorResult,
        code_context: Dict[str, str],
        test_command: str = "pytest",
        round_number: int = 1,
        failed_evidence: Optional[Any] = None,
    ) -> DefenderResult:
        """Compatibility wrapper for analyze."""
        return await self.analyze(
            bug_description=bug_description,
            repository_context=code_context,
            prosecutor_result=prosecutor_result,
            previous_evidence=failed_evidence,
            round_number=round_number
        )

    def _generate_mock_result(
        self,
        bug_description: str,
        prosecutor_result: ProsecutorResult,
        formatted_repo: str,
        round_number: int,
        failed_evidence: Optional[str] = None,
    ) -> DefenderResult:
        """Deterministic mock fallback when API key is unconfigured and fallback is permitted."""
        target_file = "processor.py"
        if round_number == 1:
            evidence_items = [
                "batch_size is not validated before iteration begins",
                "Non-positive batch_size (<= 0) causes ValueError/infinite loop",
                "Streaming generator inputs lacking __len__ raise TypeError under Fix A"
            ]
            return DefenderResult(
                challenge="Prosecutor's Fix A is naive: the loop boundary is not the only issue and Fix A causes regressions on non-positive batch sizes and generator inputs.",
                alternative_hypothesis="The caller contract must validate batch_size and normalize iterable inputs, not merely adjust the range stop index.",
                evidence=evidence_items,
                affected_files=[target_file],
                proposed_patch="""--- a/processor.py
+++ b/processor.py
@@ -35,7 +35,11 @@
+    if batch_size <= 0:
+        raise ValueError("batch_size must be positive integer")
     batches = []
-    for i in range(0, len(items) + 1, batch_size):
+    item_list = list(items)
+    for i in range(0, len(item_list), batch_size):
         batches.append(item_list[i:i + batch_size])
""",
                reasoning_summary="Fix B converts input safely, validates positive batch_size, and eliminates boundary overflow while supporting any iterable."
            )
        else:
            return DefenderResult(
                challenge=f"Prosecutor's Round {round_number} patch only checks truthiness without distinguishing None from empty list.",
                alternative_hypothesis="Explicit None check and type normalization required to prevent downstream NoneType attribute errors.",
                evidence=[
                    "Input items=None causes TypeError: 'NoneType' object is not iterable",
                    "Truthiness check incorrectly equates empty list with None"
                ],
                affected_files=[target_file],
                proposed_patch="""--- a/processor.py
+++ b/processor.py
@@ -10,4 +10,6 @@
+    if items is None:
+        return []
""",
                reasoning_summary="Fix B guarantees deterministic empty list return for both None and empty collections."
            )
