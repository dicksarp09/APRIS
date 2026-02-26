import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class MetricsDatabase:
    def __init__(self, db_path: str = "workflow.db"):
        self.db_path = db_path
        self._init_metrics_table()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_metrics_table(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    metadata_json TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    temperature REAL,
                    prompt_version TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    latency REAL,
                    cost REAL,
                    status TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS systemic_issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_signature TEXT NOT NULL,
                    first_occurrence TEXT NOT NULL,
                    last_occurrence TEXT NOT NULL,
                    count INTEGER DEFAULT 1,
                    systemic_issue INTEGER DEFAULT 0,
                    alert_logged INTEGER DEFAULT 0
                )
            """)

            conn.commit()

    def record_metric(
        self,
        workflow_id: str,
        metric_name: str,
        metric_value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        import json

        timestamp = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO metrics (workflow_id, timestamp, metric_name, metric_value, metadata_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (workflow_id, timestamp, metric_name, metric_value, metadata_json),
            )
            conn.commit()

    def record_llm_call(
        self,
        workflow_id: str,
        model: str,
        temperature: float,
        prompt_version: str,
        input_tokens: int,
        output_tokens: int,
        latency: float,
        cost: float,
        status: str,
    ) -> None:
        timestamp = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO llm_calls 
                   (workflow_id, timestamp, model, temperature, prompt_version, input_tokens, output_tokens, latency, cost, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    workflow_id,
                    timestamp,
                    model,
                    temperature,
                    prompt_version,
                    input_tokens,
                    output_tokens,
                    latency,
                    cost,
                    status,
                ),
            )
            conn.commit()

    def get_workflow_metrics(self, workflow_id: str) -> List[Dict[str, Any]]:
        import json

        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT metric_name, metric_value, timestamp, metadata_json 
                   FROM metrics WHERE workflow_id = ? ORDER BY timestamp""",
                (workflow_id,),
            )
            return [
                {
                    "metric_name": row["metric_name"],
                    "metric_value": row["metric_value"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata_json"])
                    if row["metadata_json"]
                    else None,
                }
                for row in cursor.fetchall()
            ]

    def get_llm_calls_for_workflow(self, workflow_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT model, temperature, prompt_version, input_tokens, output_tokens, latency, cost, status, timestamp
                   FROM llm_calls WHERE workflow_id = ? ORDER BY timestamp""",
                (workflow_id,),
            )
            return [
                {
                    "model": row["model"],
                    "temperature": row["temperature"],
                    "prompt_version": row["prompt_version"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "latency": row["latency"],
                    "cost": row["cost"],
                    "status": row["status"],
                    "timestamp": row["timestamp"],
                }
                for row in cursor.fetchall()
            ]

    def get_aggregated_metrics(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(DISTINCT workflow_id) as total_workflows,
                    SUM(metric_value) as total_tokens,
                    AVG(metric_value) as avg_tokens
                FROM metrics WHERE metric_name = 'tokens_used'
            """)
            row = cursor.fetchone()

            cursor2 = conn.execute("""
                SELECT COUNT(*) as total_calls, AVG(cost) as avg_cost, AVG(latency) as avg_latency
                FROM llm_calls
            """)
            row2 = cursor2.fetchone()

            cursor3 = conn.execute("""
                SELECT COUNT(*) as failures FROM llm_calls WHERE status = 'failure'
            """)
            row3 = cursor3.fetchone()

            success_rate = 1.0
            if row2["total_calls"] and row2["total_calls"] > 0:
                success_rate = (row2["total_calls"] - (row3["failures"] or 0)) / row2[
                    "total_calls"
                ]

            return {
                "total_workflows": row["total_workflows"] or 0,
                "total_tokens": row["total_tokens"] or 0,
                "avg_tokens": row["avg_tokens"] or 0,
                "total_llm_calls": row2["total_calls"] or 0,
                "avg_llm_cost": row2["avg_cost"] or 0,
                "avg_llm_latency": row2["avg_latency"] or 0,
                "llm_success_rate": success_rate,
            }

    def record_systemic_issue(
        self, error_signature: str, increment: bool = False
    ) -> bool:
        timestamp = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT count, systemic_issue FROM systemic_issues WHERE error_signature = ?",
                (error_signature,),
            )
            row = cursor.fetchone()

            if row:
                new_count = row["count"] + 1 if increment else 1
                systemic = 1 if new_count >= 5 else 0
                conn.execute(
                    """UPDATE systemic_issues 
                       SET count = ?, last_occurrence = ?, systemic_issue = ?
                       WHERE error_signature = ?""",
                    (new_count, timestamp, systemic, error_signature),
                )
            else:
                conn.execute(
                    """INSERT INTO systemic_issues 
                       (error_signature, first_occurrence, last_occurrence, count, systemic_issue)
                       VALUES (?, ?, ?, ?, 0)""",
                    (error_signature, timestamp, timestamp),
                )
            conn.commit()

            if row and (row["count"] + 1 if increment else 1) >= 5:
                return True
        return False

    def get_systemic_issues(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT error_signature, first_occurrence, last_occurrence, count, systemic_issue FROM systemic_issues WHERE systemic_issue = 1"
            )
            return [
                {
                    "error_signature": row["error_signature"],
                    "first_occurrence": row["first_occurrence"],
                    "last_occurrence": row["last_occurrence"],
                    "count": row["count"],
                }
                for row in cursor.fetchall()
            ]

    def log_alert(self, error_signature: str, alert_type: str) -> None:
        timestamp = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE systemic_issues SET alert_logged = 1 WHERE error_signature = ?",
                (error_signature,),
            )
            conn.commit()


_metrics_db: Optional[MetricsDatabase] = None


def get_metrics_database() -> MetricsDatabase:
    global _metrics_db
    if _metrics_db is None:
        _metrics_db = MetricsDatabase()
    return _metrics_db
