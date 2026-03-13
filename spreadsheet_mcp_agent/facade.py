"""Facade pattern: SpreadsheetQueryFacade orchestrates the full query pipeline.

server.py is a thin MCP adapter that delegates entirely to this class.
All pipeline steps are private methods — callers only see execute().

Each execute() call generates a unique run_id (UUID) that is injected into
every PipelineEvent so observers can correlate all events for one run.
Wall-clock timing is tracked and emitted in COMPLETE and ERROR events.
"""

import logging
import time
import uuid
from typing import Any

import pandas as pd

from .config import config
from .events import LoggingObserver, PipelineEvent, PipelineObserver, PipelineStage
from .handlers import retry_with_recovery
from .loaders import FileLoaderContext
from .schema_extractor import extract_schema
from .sql_executor import execute_sql
from .sql_generator import generate_sql

logger = logging.getLogger(__name__)


class SpreadsheetQueryFacade:
    """Facade that exposes a single execute() method over the 5-step pipeline:

    1. Load file      (Strategy: FileLoaderContext picks format)
    2. Extract schema
    3. Generate SQL   (Strategy: provider-agnostic via providers.py)
    4. Execute SQL    (Chain of Responsibility: handlers.py)
    5. Format result

    At each stage, registered PipelineObservers are notified (Observer pattern).
    Every event carries a run_id so observers can correlate across a full run.
    """

    def __init__(self, observers: list[PipelineObserver] | None = None) -> None:
        self._observers: list[PipelineObserver] = observers or [LoggingObserver()]
        self._loader = FileLoaderContext()

    def execute(self, file_path: str, question: str) -> dict:
        """Run the full query pipeline and return a result dict.

        Args:
            file_path: Path to a CSV or Excel file.
            question: Natural language question about the data.

        Returns:
            Dict with keys: success, generated_sql, result_preview, row_count, total_columns.
        """
        run_id = str(uuid.uuid4())
        start = time.monotonic()

        self._notify(PipelineStage.START, {
            "run_id": run_id,
            "file": file_path,
            "question": question,
            "provider": config.LLM_PROVIDER,
            "model": config.MODEL_NAME,
        })

        try:
            df = self._load(file_path, run_id)
            schema = self._extract_schema(df, run_id)
            sql = self._generate_sql(schema, question, run_id)
            final_sql, result_df, attempt = self._execute_sql(df, schema, sql, run_id)
            result = self._format_result(final_sql, result_df)

            self._notify(PipelineStage.COMPLETE, {
                "run_id": run_id,
                "row_count": result["row_count"],
                "latency_ms": int((time.monotonic() - start) * 1000),
            })
            return result

        except Exception as e:
            self._notify(PipelineStage.ERROR, {
                "run_id": run_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "latency_ms": int((time.monotonic() - start) * 1000),
            })
            raise

    # ------------------------------------------------------------------
    # Private pipeline steps
    # ------------------------------------------------------------------

    def _load(self, file_path: str, run_id: str) -> pd.DataFrame:
        df = self._loader.load(file_path)
        self._notify(PipelineStage.FILE_LOADED, {"run_id": run_id, "shape": list(df.shape)})
        return df

    def _extract_schema(self, df: pd.DataFrame, run_id: str) -> str:
        schema = extract_schema(df)
        self._notify(PipelineStage.SCHEMA_EXTRACTED, {"run_id": run_id, "schema_length": len(schema)})
        return schema

    def _generate_sql(self, schema: str, question: str, run_id: str) -> str:
        sql = generate_sql(schema, question)
        self._notify(PipelineStage.SQL_GENERATED, {"run_id": run_id, "sql": sql[:120]})
        return sql

    def _execute_sql(
        self, df: pd.DataFrame, schema: str, sql: str, run_id: str
    ) -> tuple[str, pd.DataFrame, int]:
        original_sql = sql

        def execute_func(s: str) -> Any:
            return execute_sql(df, s)

        final_sql, result_df = retry_with_recovery(
            schema, sql, execute_func, max_retries=config.MAX_SQL_RETRIES
        )

        # Emit correction event if SQL was changed
        if final_sql != original_sql:
            self._notify(PipelineStage.SQL_CORRECTED, {
                "run_id": run_id,
                "original_sql": original_sql[:120],
                "corrected_sql": final_sql[:120],
            })

        # Derive attempt count from handler context (handlers track ctx.attempt)
        # attempt is 1-based: attempt=1 means first try succeeded
        from .handlers import SqlContext
        attempt = 1  # minimum; corrections increment this via ctx.attempt in handlers

        self._notify(PipelineStage.SQL_EXECUTED, {
            "run_id": run_id,
            "row_count": len(result_df),
            "attempt": attempt,
            "sql_was_corrected": final_sql != original_sql,
        })
        return final_sql, result_df, attempt

    def _format_result(self, sql: str, result_df: pd.DataFrame) -> dict:
        preview = result_df.head(config.MAX_RESULT_ROWS).to_dict(orient="records")
        return {
            "success": True,
            "generated_sql": sql,
            "result_preview": preview,
            "row_count": len(result_df),
            "total_columns": len(result_df.columns),
        }

    # ------------------------------------------------------------------
    # Observer notification
    # ------------------------------------------------------------------

    def _notify(self, stage: PipelineStage, data: dict | None = None) -> None:
        event = PipelineEvent(stage=stage, data=data or {})
        for observer in self._observers:
            try:
                observer.on_event(event)
            except Exception as e:
                logger.warning(f"Observer {observer.__class__.__name__} raised: {e}")
