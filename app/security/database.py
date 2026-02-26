import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime


class DatabaseManager:
    _instance = None

    def __new__(cls, db_path: str = "workflow.db"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._db_path = db_path
            cls._instance._init_database()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    role TEXT CHECK(role IN ('viewer','operator','admin')) NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    repo_url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    reflection_count INTEGER DEFAULT 0,
                    current_node TEXT,
                    state_json TEXT,
                    user_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL,
                    error_type TEXT,
                    details_json TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_workflow 
                ON audit_log(workflow_id, timestamp)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS node_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    result_json TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    inputs_hash TEXT NOT NULL,
                    outputs_hash TEXT NOT NULL,
                    reasoning_summary TEXT,
                    latency REAL,
                    token_usage INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    status TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_steps 
                ON workflow_steps(workflow_id, timestamp)
            """)

            conn.commit()

    def create_workflow(
        self, workflow_id: str, repo_url: str, state_json: str, user_id: str = None
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO workflows (workflow_id, repo_url, status, state_json, user_id, created_at, updated_at)
                VALUES (?, ?, 'pending', ?, ?, ?, ?)
            """,
                (workflow_id, repo_url, state_json, user_id, now, now),
            )
            conn.commit()

    def update_workflow_state(
        self,
        workflow_id: str,
        state_json: str,
        status: str,
        confidence: float,
        current_node: Optional[str] = None,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE workflows 
                SET state_json = ?, status = ?, confidence = ?, current_node = ?, updated_at = ?
                WHERE workflow_id = ?
            """,
                (state_json, status, confidence, current_node, now, workflow_id),
            )
            conn.commit()

    def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT state_json, status, confidence, reflection_count, current_node, user_id
                FROM workflows WHERE workflow_id = ?
            """,
                (workflow_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "state_json": row["state_json"],
                    "status": row["status"],
                    "confidence": row["confidence"],
                    "reflection_count": row["reflection_count"],
                    "current_node": row["current_node"],
                    "user_id": row["user_id"],
                }
            return None

    def get_workflow_status(self, workflow_id: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT status FROM workflows WHERE workflow_id = ?", (workflow_id,)
            )
            row = cursor.fetchone()
            return row["status"] if row else None

    def increment_reflection_count(self, workflow_id: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE workflows SET reflection_count = reflection_count + 1 
                WHERE workflow_id = ?
                RETURNING reflection_count
            """,
                (workflow_id,),
            )
            conn.commit()
            row = cursor.fetchone()
            return row["reflection_count"] if row else 0

    def append_audit_log(
        self,
        workflow_id: str,
        node_name: str,
        status: str,
        confidence: float,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        import json

        timestamp = datetime.utcnow().isoformat()
        details_json = json.dumps(details) if details else None
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_log (workflow_id, node_name, timestamp, status, confidence, error_type, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    workflow_id,
                    node_name,
                    timestamp,
                    status,
                    confidence,
                    error_type,
                    details_json,
                ),
            )
            conn.commit()

    def get_audit_log(self, workflow_id: str) -> List[Dict[str, Any]]:
        import json

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT node_name, timestamp, status, confidence, error_type, details_json
                FROM audit_log WHERE workflow_id = ? ORDER BY timestamp
            """,
                (workflow_id,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "node_name": row["node_name"],
                    "timestamp": row["timestamp"],
                    "status": row["status"],
                    "confidence": row["confidence"],
                    "error_type": row["error_type"],
                    "details": json.loads(row["details_json"])
                    if row["details_json"]
                    else None,
                }
                for row in rows
            ]

    def record_node_execution(
        self,
        workflow_id: str,
        node_name: str,
        status: str,
        started_at: str,
        completed_at: Optional[str] = None,
        retry_count: int = 0,
        result_json: Optional[str] = None,
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO node_executions 
                (workflow_id, node_name, status, started_at, completed_at, retry_count, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            """,
                (
                    workflow_id,
                    node_name,
                    status,
                    started_at,
                    completed_at,
                    retry_count,
                    result_json,
                ),
            )
            conn.commit()
            row = cursor.fetchone()
            return row["id"] if row else -1

    def update_node_execution(
        self,
        execution_id: int,
        status: str,
        completed_at: str,
        result_json: Optional[str] = None,
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE node_executions 
                SET status = ?, completed_at = ?, result_json = ?
                WHERE id = ?
            """,
                (status, completed_at, result_json, execution_id),
            )
            conn.commit()

    def get_last_successful_node(self, workflow_id: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT node_name FROM node_executions
                WHERE workflow_id = ? AND status = 'success'
                ORDER BY completed_at DESC LIMIT 1
            """,
                (workflow_id,),
            )
            row = cursor.fetchone()
            return row["node_name"] if row else None

    def list_incomplete_workflows(self) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT workflow_id FROM workflows 
                WHERE status IN ('pending', 'in_progress', 'retrying', 'awaiting_approval')
                ORDER BY created_at
            """)
            return [row["workflow_id"] for row in cursor.fetchall()]

    def append_workflow_step(
        self,
        workflow_id: str,
        step_id: str,
        agent_name: str,
        inputs_hash: str,
        outputs_hash: str,
        reasoning_summary: Optional[str] = None,
        latency: Optional[float] = None,
        token_usage: int = 0,
        cost: float = 0.0,
        status: str = "success",
    ) -> None:
        timestamp = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO workflow_steps 
                (workflow_id, step_id, timestamp, agent_name, inputs_hash, outputs_hash, 
                 reasoning_summary, latency, token_usage, cost, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    workflow_id,
                    step_id,
                    timestamp,
                    agent_name,
                    inputs_hash,
                    outputs_hash,
                    reasoning_summary,
                    latency,
                    token_usage,
                    cost,
                    status,
                ),
            )
            conn.commit()

    def get_workflow_steps(self, workflow_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT step_id, timestamp, agent_name, inputs_hash, outputs_hash,
                       reasoning_summary, latency, token_usage, cost, status
                FROM workflow_steps WHERE workflow_id = ? ORDER BY timestamp
            """,
                (workflow_id,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "step_id": row["step_id"],
                    "timestamp": row["timestamp"],
                    "agent_name": row["agent_name"],
                    "inputs_hash": row["inputs_hash"],
                    "outputs_hash": row["outputs_hash"],
                    "reasoning_summary": row["reasoning_summary"],
                    "latency": row["latency"],
                    "token_usage": row["token_usage"],
                    "cost": row["cost"],
                    "status": row["status"],
                }
                for row in rows
            ]

    def get_cost_summary(self, workflow_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT SUM(cost) as total_cost, SUM(token_usage) as total_tokens,
                       COUNT(*) as total_steps
                FROM workflow_steps WHERE workflow_id = ?
            """,
                (workflow_id,),
            )
            row = cursor.fetchone()
            return {
                "total_cost": row["total_cost"] or 0.0,
                "total_tokens": row["total_tokens"] or 0,
                "total_steps": row["total_steps"] or 0,
            }

    def get_failure_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT step_id, timestamp, agent_name, reasoning_summary, status
                FROM workflow_steps 
                WHERE workflow_id = ? AND status = 'failure'
                ORDER BY timestamp
            """,
                (workflow_id,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "step_id": row["step_id"],
                    "timestamp": row["timestamp"],
                    "agent_name": row["agent_name"],
                    "reasoning_summary": row["reasoning_summary"],
                    "status": row["status"],
                }
                for row in rows
            ]

    def create_user(self, user_id: str, role: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO users (user_id, role, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, role, now, now),
            )
            conn.commit()

    def get_user_role(self, user_id: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT role FROM users WHERE user_id = ?", (user_id,)
            )
            row = cursor.fetchone()
            return row["role"] if row else None

    def list_users(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT user_id, role, created_at FROM users")
            return [
                {
                    "user_id": row["user_id"],
                    "role": row["role"],
                    "created_at": row["created_at"],
                }
                for row in cursor.fetchall()
            ]


_db_instance: Optional[DatabaseManager] = None


def get_database(db_path: str = "workflow.db") -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager(db_path)
    return _db_instance


def reset_database():
    global _db_instance
    _db_instance = None
