import logging
from typing import Optional, Tuple
from backend.evidence.collector import EvidenceCollector
from backend.schemas.session import Session, RoundState
from backend.schemas.agents import JudgeResult

logger = logging.getLogger(__name__)


class RoundManager:
    """
    Coordinates state transitions between debate rounds.
    Guarantees that failed evidence is systematically forwarded into subsequent rounds.
    """

    def __init__(self, session: Session, collector: EvidenceCollector):
        self.session = session
        self.collector = collector
        self.current_round = session.current_round
        self.max_rounds = session.max_rounds
        self.carried_failure_evidence: Optional[str] = None

    def should_continue(self, judge_result: Optional[JudgeResult]) -> Tuple[bool, str]:
        """
        Determines if another adversarial round is required.
        Actual test execution is the source of truth:
        If verified by test execution -> stop.
        If round limit reached -> stop with failure.
        Otherwise -> continue.
        """
        if judge_result:
            if judge_result.decision in ("VERIFIED", "MULTIPLE_VALID_FIXES"):
                return False, f"Fix verified by actual test execution in Round {self.current_round}!"

        if self.current_round >= self.max_rounds:
            return False, f"Max debate rounds ({self.max_rounds}) reached without verified fix."

        return True, "Proceeding to next adversarial round with carried failure evidence."

    def prepare_next_round(self, judge_result: JudgeResult):
        """Prepares failed evidence dossier for the next round."""
        self.current_round += 1
        self.session.current_round = self.current_round

        # Carry failed traces into next round from JudgeExecutionDetails
        failures = []
        patch_a = judge_result.execution.patch_a
        patch_b = judge_result.execution.patch_b

        if patch_a and patch_a.status != "passed":
            failures.append(f"Patch A failed tests: {patch_a.stderr or patch_a.stdout}")
        if patch_b and patch_b.status != "passed":
            failures.append(f"Patch B failed tests: {patch_b.stderr or patch_b.stdout}")

        self.carried_failure_evidence = "\n".join(failures) if failures else "Tests failed in previous sandbox execution."
        logger.info(f"Carried failure evidence to Round {self.current_round}: {self.carried_failure_evidence[:120]}...")
