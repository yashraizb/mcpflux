"""Observer pattern: pipeline events and observer interface.

Persistent observers:
- JsonlObserver  — appends one JSON line per event to a .jsonl file (immediate flush)
- SqliteObserver — writes one row per completed run to a SQLite database
Both survive MCP server process death since data is written to disk immediately.
"""

import json
import logging
import os
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

class PipelineStage(str, Enum):
    START = "start"
    FILE_LOADED = "file_loaded"
    SCHEMA_EXTRACTED = "schema_extracted"
    SQL_GENERATED = "sql_generated"
    SQL_CORRECTED = "sql_corrected"
    SQL_DECOMPOSED = "sql_decomposed"
    SQL_EXECUTED = "sql_executed"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class PipelineEvent:
    stage: PipelineStage
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Observer interface
# ---------------------------------------------------------------------------

class PipelineObserver(ABC):
    @abstractmethod
    def on_event(self, event: PipelineEvent) -> None: ...


# ---------------------------------------------------------------------------
# Built-in observers
# ---------------------------------------------------------------------------

class LoggingObserver(PipelineObserver):
    """Default observer: logs every pipeline event to Python logger."""

    def on_event(self, event: PipelineEvent) -> None:
        logger.info(f"[{event.stage.value}] {event.data}")


class MetricsObserver(PipelineObserver):
    """Placeholder observer for push-based metrics sinks (Prometheus, Datadog, etc.)."""

    def on_event(self, event: PipelineEvent) -> None:
        pass  # plug in metrics client here


class JsonlObserver(PipelineObserver):
    """Appends one JSON line per event to a .jsonl file.

    Written with immediate flush so nothing is lost if the MCP server process
    is killed by Claude Desktop exiting. All events for one pipeline run share
    the same run_id (injected by the facade) for correlation.

    Default path: ~/.mcpflux/events.jsonl
    Override via EVENTS_LOG_PATH env var or constructor argument.
    """

    def __init__(self, log_path: str | None = None) -> None:
        path = log_path or os.getenv("EVENTS_LOG_PATH") or str(
            Path.home() / ".mcpflux" / "events.jsonl"
        )
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"JsonlObserver writing to {self._path}")

    def on_event(self, event: PipelineEvent) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "stage": event.stage.value,
            "data": event.data,
        }
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
            f.flush()  # immediate flush — safe against process death


class SqliteObserver(PipelineObserver):
    """Writes one row per completed pipeline run to a SQLite database.

    Accumulates events in memory during a run (keyed by run_id), then flushes
    a single row on COMPLETE or ERROR. Enables post-hoc queries like:
        SELECT provider, AVG(success)*100 FROM pipeline_runs GROUP BY provider;
        SELECT AVG(corrections) FROM pipeline_runs WHERE success=1;
        SELECT question, latency_ms FROM pipeline_runs ORDER BY latency_ms DESC LIMIT 10;

    Default path: ~/.mcpflux/metrics.db
    Override via METRICS_DB_PATH env var or constructor argument.
    """

    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id      TEXT    NOT NULL,
        ts          TEXT    NOT NULL,
        file_path   TEXT,
        question    TEXT,
        provider    TEXT,
        model       TEXT,
        success     INTEGER NOT NULL DEFAULT 0,
        attempts    INTEGER DEFAULT 0,
        corrections INTEGER DEFAULT 0,
        latency_ms  INTEGER,
        error       TEXT
    );
    """

    def __init__(self, db_path: str | None = None) -> None:
        path = db_path or os.getenv("METRICS_DB_PATH") or str(
            Path.home() / ".mcpflux" / "metrics.db"
        )
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(self._CREATE_TABLE)
        self._conn.commit()
        self._runs: dict[str, dict] = {}  # run_id → accumulated data
        logger.info(f"SqliteObserver writing to {path}")

    def on_event(self, event: PipelineEvent) -> None:
        run_id = event.data.get("run_id", "unknown")

        if event.stage == PipelineStage.START:
            self._runs[run_id] = {
                "run_id": run_id,
                "ts": datetime.now(timezone.utc).isoformat(),
                "file_path": event.data.get("file"),
                "question": event.data.get("question"),
                "provider": event.data.get("provider"),
                "model": event.data.get("model"),
                "corrections": 0,
                "attempts": 0,
            }

        elif event.stage == PipelineStage.SQL_CORRECTED:
            if run_id in self._runs:
                self._runs[run_id]["corrections"] += 1

        elif event.stage == PipelineStage.SQL_EXECUTED:
            if run_id in self._runs:
                self._runs[run_id]["attempts"] = event.data.get("attempt", 1)

        elif event.stage == PipelineStage.COMPLETE:
            self._flush(run_id, success=True, latency_ms=event.data.get("latency_ms"), error=None)

        elif event.stage == PipelineStage.ERROR:
            self._flush(
                run_id,
                success=False,
                latency_ms=event.data.get("latency_ms"),
                error=event.data.get("error"),
            )

    def _flush(self, run_id: str, success: bool, latency_ms: int | None, error: str | None) -> None:
        run = self._runs.pop(run_id, {})
        if not run:
            return
        self._conn.execute(
            """INSERT INTO pipeline_runs
               (run_id, ts, file_path, question, provider, model,
                success, attempts, corrections, latency_ms, error)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run.get("run_id"),
                run.get("ts"),
                run.get("file_path"),
                run.get("question"),
                run.get("provider"),
                run.get("model"),
                1 if success else 0,
                run.get("attempts", 0),
                run.get("corrections", 0),
                latency_ms,
                error,
            ),
        )
        self._conn.commit()
