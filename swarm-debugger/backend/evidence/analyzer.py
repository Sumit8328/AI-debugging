import re
from typing import Dict, Any, List, Optional
from backend.schemas.execution import ExecutionResult


class EvidenceAnalyzer:
    """
    Analyzes sandbox execution logs to extract actionable forensic artifacts.
    """

    @staticmethod
    def extract_failures(execution: ExecutionResult) -> List[str]:
        """Extracts individual test failure summaries and tracebacks from stdout/stderr."""
        failures = []
        if execution.status == "passed":
            return failures

        lines = (execution.stdout + "\n" + execution.stderr).splitlines()
        capturing = False
        current_failure = []

        for line in lines:
            if line.startswith("FAILED ") or line.startswith("E   "):
                failures.append(line.strip())
            elif "___ " in line and " ___" in line:
                current_failure.append(line.strip())
            elif line.startswith("=========================== FAILURES"):
                capturing = True

        if not failures and execution.stderr:
            failures.append(execution.stderr.strip())

        return failures or [f"Execution failed with exit code {execution.exit_code}"]
