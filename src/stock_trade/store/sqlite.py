from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stock_trade.events.models import Event


class SQLiteStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def create_run(
        self,
        run_id: str,
        mode: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO runs (run_id, mode, status, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    mode = excluded.mode,
                    status = excluded.status,
                    metadata_json = excluded.metadata_json
                """,
                (run_id, mode, status, json.dumps(metadata or {}), now),
            )

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT run_id, mode, status, metadata_json, created_at FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return _run_from_row(row)

    def list_runs(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT run_id, mode, status, metadata_json, created_at
                FROM runs
                ORDER BY created_at
                """
            ).fetchall()
        return [_run_from_row(row) for row in rows]

    def append_event(self, event: Event) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO events (event_id, run_id, event_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event.event_id, event.run_id, event.to_json(), event.ts.isoformat()),
            )

    def list_events(self, run_id: str) -> list[Event]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT event_json FROM events WHERE run_id = ? ORDER BY rowid",
                (run_id,),
            ).fetchall()
        return [Event.from_json(row[0]) for row in rows]

    def list_all_events(self) -> list[Event]:
        with self._connection() as connection:
            rows = connection.execute("SELECT event_json FROM events ORDER BY rowid").fetchall()
        return [Event.from_json(row[0]) for row in rows]

    def save_plan(self, run_id: str, plan: dict[str, Any]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO plans (run_id, plan_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    plan_json = excluded.plan_json,
                    updated_at = excluded.updated_at
                """,
                (run_id, json.dumps(plan), now),
            )

    def get_plan(self, run_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT plan_json FROM plans WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return json.loads(row[0])

    def save_agent_trace(self, run_id: str, agent_name: str, trace: dict[str, Any]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO agent_traces (run_id, agent_name, trace_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, agent_name, json.dumps(trace), now),
            )

    def get_trace(self, run_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT agent_name, trace_json
                FROM agent_traces
                WHERE run_id = ?
                ORDER BY created_at, id
                """,
                (run_id,),
            ).fetchall()
        return [{"agent_name": row[0], "trace": json.loads(row[1])} for row in rows]

    def journal_mode(self) -> str:
        with self._connection() as connection:
            row = connection.execute("PRAGMA journal_mode").fetchone()
        return str(row[0]).lower()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_events_run_id_created_at
                    ON events(run_id, created_at);

                CREATE TABLE IF NOT EXISTS plans (
                    run_id TEXT PRIMARY KEY,
                    plan_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS agent_traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    trace_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_agent_traces_run_id_created_at
                    ON agent_traces(run_id, created_at);
                """
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        with closing(self._connect()) as connection, connection:
            yield connection

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection


def _run_from_row(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    return {
        "run_id": row[0],
        "mode": row[1],
        "status": row[2],
        "metadata": json.loads(row[3]),
        "created_at": row[4],
    }