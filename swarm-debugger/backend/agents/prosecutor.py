import logging
from typing import Optional, Dict, Any, List, Union
from backend.config import settings
from backend.schemas.agents import ProsecutorResult
from backend.agents.prompts import PROSECUTOR_SYSTEM_PROMPT
from backend.ai.client import get_openai_client, OpenAIClient, OpenAIConfigurationError

logger = logging.getLogger(__name__)


def format_repository_context(repo_context: Union[str, Dict[str, str]]) -> str:
    """Formats repository files into structured string context."""
    if isinstance(repo_context, dict):
        parts = []
        for file_path, content in repo_context.items():
            parts.append(f"=== File: {file_path} ===\n{content}\n")
        return "\n".join(parts)
    return str(repo_context or "")


def format_previous_evidence(prev_evidence: Optional[Union[str, List[str]]]) -> Optional[str]:
    """Formats previous evidence into string or None."""
    if isinstance(prev_evidence, list):
        return "\n".join(f"- {item}" for item in prev_evidence) if prev_evidence else None
    return prev_evidence


class ProsecutorAgent:
    """
    Prosecutor Agent in adversarial software debugging system.
    Investigates the reported bug and constructs the strongest evidence-based hypothesis.
    Proposes Fix A as a candidate patch.
    """

    def __init__(self, client: Optional[OpenAIClient] = None, allow_fallback: bool = False):
        self.client = client or get_openai_client()
        self.allow_fallback = allow_fallback

    async def analyze(
        self,
        bug_description: str,
        repository_context: Union[str, Dict[str, str]],
        previous_evidence: Optional[Union[str, List[str]]] = None,
        **kwargs: Any
    ) -> ProsecutorResult:
        """
        1. Build the Prosecutor system prompt.
        2. Build a structured user input containing:
           - bug description
           - repository context
           - previous evidence
        3. Call the OpenAI Responses API.
        4. Request structured output.
        5. Validate the result using ProsecutorResult.
        6. Return ProsecutorResult.
        """
        formatted_repo = format_repository_context(repository_context)
        formatted_evidence = format_previous_evidence(previous_evidence)

        # Check if OpenAI client is configured
        if not self.client.is_configured():
            if self.allow_fallback:
                logger.warning("OpenAI API key not set; falling back to deterministic mock artifact")
                round_num = kwargs.get("round_number", 1)
                return self._generate_mock_result(bug_description, formatted_repo, round_num, formatted_evidence)
            raise OpenAIConfigurationError("OpenAI API configuration is missing.")

        # 1. Build system instructions
        instructions = PROSECUTOR_SYSTEM_PROMPT

        # 2. Build structured user input
        user_input_parts = [
            f"REPORTED BUG:\n{bug_description}\n",
            f"REPOSITORY CONTEXT:\n{formatted_repo}\n"
        ]
        if formatted_evidence:
            user_input_parts.append(f"PREVIOUS ROUND EVIDENCE:\n{formatted_evidence}\n")
        else:
            user_input_parts.append("PREVIOUS ROUND EVIDENCE:\nNone (Round 1 initial investigation)\n")

        user_input_parts.append(
            "Construct your evidence-based indictment of the root cause, identify affected files, and formulate Fix A."
        )
        user_input = "\n".join(user_input_parts)

        # 3. Call OpenAI Responses API with structured output
        logger.info(f"Prosecutor calling OpenAI Responses API ({self.client.model_name})...")
        result = await self.client.create_response(
            instructions=instructions,
            input_text=user_input,
            response_format=ProsecutorResult
        )

        # 4 & 5. Validate output with ProsecutorResult
        validated: ProsecutorResult = ProsecutorResult.model_validate(result)
        logger.info(f"Prosecutor generated validated indictment: {validated.root_cause[:80]}...")
        return validated

    async def investigate_and_propose(
        self,
        bug_description: str,
        code_context: Dict[str, str],
        test_command: str = "pytest",
        round_number: int = 1,
        failed_evidence: Optional[Any] = None,
    ) -> ProsecutorResult:
        """Compatibility wrapper for analyze."""
        return await self.analyze(
            bug_description=bug_description,
            repository_context=code_context,
            previous_evidence=failed_evidence,
            round_number=round_number
        )

    def _generate_mock_result(
        self,
        bug_description: str,
        formatted_repo: str,
        round_number: int,
        failed_evidence: Optional[str] = None,
    ) -> ProsecutorResult:
        """Deterministic mock fallback when API key is unconfigured and fallback is permitted."""
        target_file = "processor.py"
        if round_number == 1:
            evidence_items = [
                "range() uses len(items) + 1 in loop termination condition",
                "The failing test reports an IndexError: list index out of range during boundary condition"
            ]
            return ProsecutorResult(
                root_cause="The loop iterates one position beyond the valid range due to an off-by-one boundary failure.",
                evidence=evidence_items,
                affected_files=[target_file],
                proposed_patch="""--- a/processor.py
+++ b/processor.py
@@ -39,5 +39,5 @@
-    for i in range(0, len(items) + 1, batch_size):
+    for i in range(0, len(items), batch_size):
         batches.append(items[i:i + batch_size])
""",
                reasoning_summary="The extra iteration causes an out-of-range access when collection size is an exact multiple of batch_size."
            )
        else:
            return ProsecutorResult(
                root_cause=f"Residual edge-case in round {round_number}: empty payload raises unhandled ZeroDivisionError.",
                evidence=[
                    f"Round {round_number - 1} test execution failed on empty collection input",
                    "Downstream caller raises ZeroDivisionError on empty payload"
                ],
                affected_files=[target_file],
                proposed_patch="""--- a/processor.py
+++ b/processor.py
@@ -12,3 +12,6 @@
+    if not items:
+        return []
""",
                reasoning_summary="Guard clause must precede batching to gracefully return empty list for empty inputs."
            )
