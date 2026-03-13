"""Chain of Responsibility pattern: SQL execution + LLM-driven error correction.

Chain: ExecuteHandler → CorrectionHandler → ExhaustedHandler

Each handler either resolves the SqlContext or passes it to the next handler.
CorrectionHandler asks the LLM to fix bad SQL, then re-triggers ExecuteHandler.
ExhaustedHandler raises when all retries are consumed.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from .llm_client import RetryDecorator, get_llm
from .sql_generator import extract_sql_from_response

logger = logging.getLogger(__name__)

_SQL_CORRECTION_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a SQL expert. The following SQL query produced an error:

Schema:
{schema}

Original SQL:
{original_sql}

Error:
{error_message}

Please provide a corrected SQL query that fixes this error. Output ONLY the SQL query, no explanations or markdown."""),
])

_correction_chain = RetryDecorator(
    _SQL_CORRECTION_PROMPT
    | get_llm()
    | StrOutputParser()
    | RunnableLambda(extract_sql_from_response)
)


# ---------------------------------------------------------------------------
# Context object passed through the handler chain
# ---------------------------------------------------------------------------

@dataclass
class SqlContext:
    schema: str
    sql: str
    execute_func: Callable[[str], Any]
    max_retries: int = 3
    attempt: int = 0
    last_error: str = ""
    result: Any = None
    success: bool = False


# ---------------------------------------------------------------------------
# Abstract handler
# ---------------------------------------------------------------------------

class SqlHandler(ABC):
    def __init__(self) -> None:
        self._next: Optional["SqlHandler"] = None

    def set_next(self, handler: "SqlHandler") -> "SqlHandler":
        self._next = handler
        return handler

    def _pass_to_next(self, ctx: SqlContext) -> SqlContext:
        if self._next:
            return self._next.handle(ctx)
        return ctx

    @abstractmethod
    def handle(self, ctx: SqlContext) -> SqlContext: ...


# ---------------------------------------------------------------------------
# Concrete handlers
# ---------------------------------------------------------------------------

class ExecuteHandler(SqlHandler):
    """Try to run the SQL. On success, marks ctx.success. On failure, passes forward."""

    def handle(self, ctx: SqlContext) -> SqlContext:
        try:
            logger.info(f"ExecuteHandler: attempt {ctx.attempt + 1}/{ctx.max_retries} — {ctx.sql[:80]}...")
            ctx.result = ctx.execute_func(ctx.sql)
            ctx.success = True
            logger.info("ExecuteHandler: execution successful")
            return ctx
        except Exception as e:
            ctx.last_error = str(e)
            ctx.attempt += 1
            logger.error(f"ExecuteHandler: failed — {ctx.last_error}")
            return self._pass_to_next(ctx)


class CorrectionHandler(SqlHandler):
    """Ask LLM to correct the SQL, then re-trigger execution from the top."""

    def __init__(self, execute_handler: "ExecuteHandler") -> None:
        super().__init__()
        self._execute_handler = execute_handler

    def handle(self, ctx: SqlContext) -> SqlContext:
        if ctx.attempt >= ctx.max_retries:
            logger.warning("CorrectionHandler: retries exhausted, passing forward")
            return self._pass_to_next(ctx)

        logger.warning(f"CorrectionHandler: correcting SQL after error — {ctx.last_error[:100]}")
        try:
            ctx.sql = _correction_chain.invoke({
                "schema": ctx.schema,
                "original_sql": ctx.sql,
                "error_message": ctx.last_error,
            })
            logger.info(f"CorrectionHandler: corrected SQL — {ctx.sql[:80]}...")
            # Re-run execution with corrected SQL
            return self._execute_handler.handle(ctx)
        except Exception as e:
            logger.error(f"CorrectionHandler: LLM correction failed — {e}")
            raise RuntimeError(
                f"SQL execution failed and LLM correction was not possible. "
                f"Last SQL error: {ctx.last_error}"
            ) from e


class ExhaustedHandler(SqlHandler):
    """Terminal handler: all retries consumed — raise."""

    def handle(self, ctx: SqlContext) -> SqlContext:
        raise RuntimeError(
            f"SQL execution failed after {ctx.max_retries} attempts. "
            f"Last error: {ctx.last_error}"
        )


# ---------------------------------------------------------------------------
# Chain factory + public API
# ---------------------------------------------------------------------------

def build_handler_chain(max_retries: int = 3) -> ExecuteHandler:
    """Build and wire the handler chain: Execute → Correction → Exhausted."""
    execute = ExecuteHandler()
    correction = CorrectionHandler(execute_handler=execute)
    exhausted = ExhaustedHandler()
    execute.set_next(correction)
    correction.set_next(exhausted)
    return execute


def retry_with_recovery(
    schema: str,
    original_sql: str,
    execute_func: Callable[[str], Any],
    max_retries: int = 3,
) -> tuple[str, Any]:
    """Public API (unchanged signature). Backed by the handler chain.

    Returns:
        Tuple of (final_sql, result_dataframe).
    """
    ctx = SqlContext(
        schema=schema,
        sql=original_sql,
        execute_func=execute_func,
        max_retries=max_retries,
    )
    result_ctx = build_handler_chain(max_retries).handle(ctx)
    return result_ctx.sql, result_ctx.result
