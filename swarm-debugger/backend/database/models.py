import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from backend.database.database import get_db_connection
from backend.schemas.session import Session, RoundState
from backend.schemas.agents import ProsecutorResult, DefenderResult, JudgeResult
from backend.schemas.execution import ExecutionResult


class SessionRepository:
    """Repository for managing Session persistence in SQLite."""

    @staticmethod
    def create_session(session: Session) -> Session:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (
                    session_id, status, bug_description, test_command, 
                    current_round, max_rounds, repository_path, demo_id, 
                    verified_patch, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.status,
                    session.bug_description,
                    session.test_command,
                    session.current_round,
                    session.max_rounds,
                    session.repository_path,
                    session.demo_id,
                    session.verified_patch,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat()
                )
            )
            conn.commit()
        return session

    @staticmethod
    def get_session(session_id: str) -> Optional[Session]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            # Fetch rounds
            cursor.execute(
                "SELECT * FROM round_artifacts WHERE session_id = ? ORDER BY round_number ASC",
                (session_id,)
            )
            round_rows = cursor.fetchall()
            rounds: List[RoundState] = []
            for r in round_rows:
                prosecutor = ProsecutorResult(**json.loads(r["prosecutor_result"])) if r["prosecutor_result"] else None
                defender = DefenderResult(**json.loads(r["defender_result"])) if r["defender_result"] else None
                judge = JudgeResult(**json.loads(r["judge_result"])) if r["judge_result"] else None
                patch_a = judge.execution.patch_a if judge else None
                patch_b = judge.execution.patch_b if judge else None

                rounds.append(RoundState(
                    round_number=r["round_number"],
                    prosecutor_result=prosecutor,
                    defender_result=defender,
                    patch_a_execution=patch_a,
                    patch_b_execution=patch_b,
                    judge_result=judge,
                    status="completed" if judge else "running",
                    failed_evidence_carried_over=r["failed_evidence"]
                ))

            return Session(
                session_id=row["session_id"],
                status=row["status"],
                bug_description=row["bug_description"],
                test_command=row["test_command"],
                current_round=row["current_round"],
                max_rounds=row["max_rounds"],
                repository_path=row["repository_path"],
                demo_id=row["demo_id"],
                verified_patch=row["verified_patch"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                rounds=rounds
            )

    @staticmethod
    def update_session_status(session_id: str, status: str, current_round: Optional[int] = None, verified_patch: Optional[str] = None):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            if current_round is not None and verified_patch is not None:
                cursor.execute(
                    "UPDATE sessions SET status = ?, current_round = ?, verified_patch = ?, updated_at = ? WHERE session_id = ?",
                    (status, current_round, verified_patch, now, session_id)
                )
            elif current_round is not None:
                cursor.execute(
                    "UPDATE sessions SET status = ?, current_round = ?, updated_at = ? WHERE session_id = ?",
                    (status, current_round, now, session_id)
                )
            elif verified_patch is not None:
                cursor.execute(
                    "UPDATE sessions SET status = ?, verified_patch = ?, updated_at = ? WHERE session_id = ?",
                    (status, verified_patch, now, session_id)
                )
            else:
                cursor.execute(
                    "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
                    (status, now, session_id)
                )
            conn.commit()

    @staticmethod
    def save_round_artifact(
        session_id: str,
        round_number: int,
        prosecutor: Optional[ProsecutorResult] = None,
        defender: Optional[DefenderResult] = None,
        judge: Optional[JudgeResult] = None,
        failed_evidence: Optional[str] = None
    ):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO round_artifacts (
                    session_id, round_number, prosecutor_result, 
                    defender_result, judge_result, failed_evidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    round_number,
                    prosecutor.model_dump_json() if prosecutor else None,
                    defender.model_dump_json() if defender else None,
                    judge.model_dump_json() if judge else None,
                    failed_evidence,
                    datetime.now(timezone.utc).isoformat()
                )
            )
            conn.commit()
