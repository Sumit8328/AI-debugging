import uuid
from typing import List, Dict, Optional
from backend.evidence.evidence_brief import EvidenceBrief, EvidenceItem
from backend.evidence.analyzer import EvidenceAnalyzer
from backend.schemas.execution import ExecutionResult


class EvidenceCollector:
    """
    Collects forensic evidence from agents and sandbox execution.
    Carries failed evidence into subsequent debate rounds.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.evidence_history: List[EvidenceBrief] = []

    def create_brief_for_round(
        self,
        round_number: int,
        execution_a: Optional[ExecutionResult] = None,
        execution_b: Optional[ExecutionResult] = None
    ) -> EvidenceBrief:
        brief = EvidenceBrief(
            session_id=self.session_id,
            round_number=round_number
        )

        # Collect failure evidence from prior round execution
        if execution_a and execution_a.status != "passed":
            fails_a = EvidenceAnalyzer.extract_failures(execution_a)
            brief.prior_failures.extend([f"[Patch A Fail] {f}" for f in fails_a])
            brief.key_evidence.append(EvidenceItem(
                item_id=str(uuid.uuid4())[:8],
                source="sandbox:patch_a",
                content=execution_a.stdout,
                failure_trace=execution_a.stderr,
                exit_code=execution_a.exit_code,
                round_discovered=round_number
            ))

        if execution_b and execution_b.status != "passed":
            fails_b = EvidenceAnalyzer.extract_failures(execution_b)
            brief.prior_failures.extend([f"[Patch B Fail] {f}" for f in fails_b])
            brief.key_evidence.append(EvidenceItem(
                item_id=str(uuid.uuid4())[:8],
                source="sandbox:patch_b",
                content=execution_b.stdout,
                failure_trace=execution_b.stderr,
                exit_code=execution_b.exit_code,
                round_discovered=round_number
            ))

        self.evidence_history.append(brief)
        return brief
