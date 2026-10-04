import sqlite3
import json
import os
from typing import Optional, Dict, Any, List
from backend.config import settings

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "swarm_debugger.db")


def get_db_connection() -> sqlite3.Connection:
    """Provides a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the SQLite schema for sessions, rounds, and evidence logs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                bug_description TEXT NOT NULL,
                test_command TEXT NOT NULL,
                current_round INTEGER NOT NULL DEFAULT 1,
                max_rounds INTEGER NOT NULL DEFAULT 3,
                repository_path TEXT,
                demo_id TEXT,
                verified_patch TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Round artifacts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS round_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                prosecutor_result TEXT,
                defender_result TEXT,
                judge_result TEXT,
                failed_evidence TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            )
        """)

        # Execution evidence logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                patch_id TEXT NOT NULL,
                status TEXT NOT NULL,
                stdout TEXT,
                stderr TEXT,
                exit_code INTEGER NOT NULL,
                tests_passed INTEGER DEFAULT 0,
                tests_failed INTEGER DEFAULT 0,
                duration_ms REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            )
        """)
        conn.commit()


# Initialize database schema on module load
init_db()
