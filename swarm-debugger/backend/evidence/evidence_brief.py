from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Single forensic evidence item."""
    item_id: str
    source: str  # e.g., "pytest", "prosecutor", "defender", "sandbox"
    content: str
    failure_trace: Optional[str] = None
    exit_code: Optional[int] = None
    round_discovered: int = 1


class EvidenceBrief(BaseModel):
    """
    Forensic dossier compiled for an ongoing adversarial debugging round.
    Failed evidence is carried into the next round.
    """
    session_id: str
    round_number: int
    prior_failures: List[str] = Field(default_factory=list)
    key_evidence: List[EvidenceItem] = Field(default_factory=list)
    unresolved_exceptions: List[str] = Field(default_factory=list)

    def summary(self) -> str:
        if not self.prior_failures:
            return "No previous round failures recorded. Initial baseline test run."
        return "\n".join(f"- {fail}" for fail in self.prior_failures)
