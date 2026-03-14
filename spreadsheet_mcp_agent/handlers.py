"""Chain of Responsibility pattern: SQL execution with proactive query decomposition.

Chain: ExecuteHandler → DecompositionHandler → ExhaustedHandler

Strategy:
1. ExecuteHandler tries the direct single SQL query.
2. On success — done.
3. On any failure — DecompositionHandler immediately breaks the question into
   sequential SQL steps and executes each one, materialising intermediate
   results as named tables so later steps can reference them.
4. If decomposition also fails — ExhaustedHandler raises a descriptive error.

This "try direct first, decompose on failure" approach avoids wasting retries
on queries that are structurally too complex for a single SQL statement.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context object passed through the handler chain
# ---------------------------------------------------------------------------

@dataclass
class SqlContext:
    schema: str
    sql: str
    execute_func: Callable[[str], Any]
    max_retries: int = 3          # kept for API compatibility; unused in new chain
    attempt: int = 0
    last_error: str = ""
    result: Any = None
    success: bool = False
    # Fields required by DecompositionHandler
    data_context: Optional[Any] = field(default=None)  # DataContext | None
    question: str = ""
    was_decomposed: bool = False  # True when DecompositionHandler handled the query


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
    """Try to run the direct SQL query.  On success, marks ctx.success.
    On any failure, passes immediately to the next handler."""

    def handle(self, ctx: SqlContext) -> SqlContext:
        try:
            logger.info(f"ExecuteHandler: trying direct query — {ctx.sql[:80]}...")
            ctx.result = ctx.execute_func(ctx.sql)
            ctx.success = True
            logger.info("ExecuteHandler: direct query succeeded")
            return ctx
        except Exception as e:
            ctx.last_error = str(e)
            ctx.attempt += 1
            logger.warning(
                f"ExecuteHandler: direct query failed — {ctx.last_error}; "
                "falling through to DecompositionHandler"
            )
            return self._pass_to_next(ctx)


class DecompositionHandler(SqlHandler):
    """Break the question into sequential SQL steps and execute them.

    When the direct query fails, this handler asks the LLM to decompose the
    question into a series of simple, focused sub-queries.  Each step's result
    is materialised as a named DataFrame added to a working copy of the
    DataContext so that subsequent steps can reference it by name.

    Falls through to the next handler if:
    - ``data_context`` or ``question`` are not set on the context
    - The LLM decomposition call fails
    - Any individual step fails to execute
    """

    def handle(self, ctx: SqlContext) -> SqlContext:
        if not ctx.data_context or not ctx.question:
            logger.warning(
                "DecompositionHandler: data_context or question not set — "
                "cannot decompose, passing forward"
            )
            return self._pass_to_next(ctx)

        logger.info("DecompositionHandler: attempting multi-step query decomposition")

        # Deferred imports avoid a circular import at module load time
        from .query_decomposer import decompose_query
        from .sql_executor import execute_sql

        try:
            steps = decompose_query(ctx.schema, ctx.question)
        except ValueError as e:
            logger.error(f"DecompositionHandler: decomposition failed — {e}")
            return self._pass_to_next(ctx)

        # Work on a shallow copy so the original DataContext is not mutated
        working_context: dict = dict(ctx.data_context)

        last_result = None
        for step in steps:
            try:
                logger.info(
                    f"DecompositionHandler: step '{step.step_name}' — "
                    f"{step.description}"
                )
                result_df = execute_sql(working_context, step.sql)
                working_context[step.step_name] = result_df
                last_result = result_df
                logger.info(
                    f"DecompositionHandler: step '{step.step_name}' "
                    f"produced {len(result_df)} rows"
                )
            except Exception as e:
                logger.error(
                    f"DecompositionHandler: step '{step.step_name}' failed — {e}"
                )
                return self._pass_to_next(ctx)

        if last_result is not None:
            ctx.result = last_result
            ctx.success = True
            ctx.sql = steps[-1].sql
            ctx.was_decomposed = True
            logger.info("DecompositionHandler: decomposed execution succeeded")
            return ctx

        return self._pass_to_next(ctx)


class ExhaustedHandler(SqlHandler):
    """Terminal handler: both direct query and decomposition failed — raise."""

    def handle(self, ctx: SqlContext) -> SqlContext:
        raise RuntimeError(
            f"Query could not be answered: the direct SQL query failed and "
            f"multi-step decomposition did not succeed. "
            f"Last error: {ctx.last_error}"
        )


# ---------------------------------------------------------------------------
# Chain factory + public API
# ---------------------------------------------------------------------------

def build_handler_chain(max_retries: int = 3) -> ExecuteHandler:
    """Build and wire the handler chain: Execute → Decompose → Exhausted.

    The ``max_retries`` parameter is accepted for API compatibility but is not
    used in the new proactive chain (decomposition happens on the first failure).
    """
    execute = ExecuteHandler()
    decomposition = DecompositionHandler()
    exhausted = ExhaustedHandler()
    execute.set_next(decomposition)
    decomposition.set_next(exhausted)
    return execute


def retry_with_recovery(
    schema: str,
    original_sql: str,
    execute_func: Callable[[str], Any],
    max_retries: int = 3,
    data_context: Optional[Any] = None,
    question: str = "",
) -> tuple[str, Any, bool]:
    """Try a direct SQL query; decompose into multi-step queries if it fails.

    The name ``retry_with_recovery`` is kept for backward compatibility.  The
    new behaviour is:
    1. Try ``original_sql`` directly.
    2. On failure, ask the LLM to decompose ``question`` into sequential steps
       and execute each step, feeding intermediate results as named tables.
    3. Raise if both paths fail.

    Args:
        schema: Schema string used by both the executor and the LLM decomposer.
        original_sql: Direct SQL generated for the question.
        execute_func: Callable that runs a SQL string and returns a DataFrame.
        max_retries: Accepted for API compatibility; not used by the new chain.
        data_context: DataContext dict required for multi-step execution.
        question: Original natural language question for the decomposer.

    Returns:
        Tuple of ``(final_sql, result_dataframe, was_decomposed)``.
    """
    ctx = SqlContext(
        schema=schema,
        sql=original_sql,
        execute_func=execute_func,
        max_retries=max_retries,
        data_context=data_context,
        question=question,
    )
    result_ctx = build_handler_chain(max_retries).handle(ctx)
    return result_ctx.sql, result_ctx.result, result_ctx.was_decomposed

