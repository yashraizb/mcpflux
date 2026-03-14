"""Tests for the proactive try-first-then-decompose query strategy.

Tests cover:
- QueryStep JSON parsing (valid, edge-cases, invalid inputs)
- decompose_query() with mocked LLM
- DecompositionHandler: multi-step execution, fallbacks, edge-cases
- ExecuteHandler: success path, immediate pass-through on failure
- build_handler_chain: new chain shape (Execute → Decompose → Exhausted)
- retry_with_recovery: direct success path and decomposed path
"""

import json
from unittest.mock import patch

import pandas as pd
import pytest

from spreadsheet_mcp_agent.handlers import (
    DecompositionHandler,
    ExecuteHandler,
    ExhaustedHandler,
    SqlContext,
    build_handler_chain,
    retry_with_recovery,
)
from spreadsheet_mcp_agent.loaders import DataContext
from spreadsheet_mcp_agent.query_decomposer import QueryStep, _parse_steps, decompose_query


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sales_context() -> DataContext:
    return {
        "sales": pd.DataFrame({
            "region": ["A", "A", "B"],
            "month": [1, 2, 1],
            "revenue": [100, 200, 150],
        })
    }


def _always_fail(sql: str):
    raise Exception(f"SQL execution failed: synthetic failure for: {sql[:30]}")


# ---------------------------------------------------------------------------
# _parse_steps
# ---------------------------------------------------------------------------

class TestParseSteps:
    def test_parses_valid_json_array(self):
        raw = json.dumps([
            {"step_name": "step_totals", "sql": "SELECT region, SUM(revenue) AS total FROM sales GROUP BY region", "description": "Monthly totals"},
            {"step_name": "step_ranked", "sql": "SELECT *, RANK() OVER (ORDER BY total DESC) AS rnk FROM step_totals", "description": "Rank by total"},
        ])
        steps = _parse_steps(raw)
        assert len(steps) == 2
        assert steps[0].step_name == "step_totals"
        assert steps[1].step_name == "step_ranked"

    def test_strips_json_markdown_fence(self):
        raw = "```json\n" + json.dumps([
            {"step_name": "step_a", "sql": "SELECT 1", "description": "d"},
        ]) + "\n```"
        steps = _parse_steps(raw)
        assert len(steps) == 1
        assert steps[0].step_name == "step_a"

    def test_strips_plain_markdown_fence(self):
        raw = "```\n" + json.dumps([
            {"step_name": "step_b", "sql": "SELECT 2", "description": "d"},
        ]) + "\n```"
        assert len(_parse_steps(raw)) == 1

    def test_empty_array_raises_value_error(self):
        with pytest.raises(ValueError, match="non-empty JSON array"):
            _parse_steps("[]")

    def test_step_missing_required_field_raises(self):
        raw = json.dumps([{"step_name": "s1", "sql": "SELECT 1"}])  # no description
        with pytest.raises(ValueError, match="missing required fields"):
            _parse_steps(raw)

    def test_invalid_json_raises(self):
        with pytest.raises((ValueError, json.JSONDecodeError)):
            _parse_steps("not json at all")


# ---------------------------------------------------------------------------
# decompose_query (LLM mocked)
# ---------------------------------------------------------------------------

class TestDecomposeQuery:
    def _steps_json(self, steps: list[dict]) -> str:
        return json.dumps(steps)

    def test_returns_query_steps_on_valid_response(self):
        payload = [
            {"step_name": "step_1", "sql": "SELECT a FROM t", "description": "d1"},
            {"step_name": "step_2", "sql": "SELECT * FROM step_1", "description": "d2"},
        ]
        with patch("spreadsheet_mcp_agent.query_decomposer._decompose_chain") as mock:
            mock.invoke.return_value = self._steps_json(payload)
            result = decompose_query("schema text", "complex question")

        assert len(result) == 2
        assert all(isinstance(s, QueryStep) for s in result)
        assert result[0].step_name == "step_1"
        assert result[1].step_name == "step_2"

    def test_raises_value_error_on_unparseable_response(self):
        with patch("spreadsheet_mcp_agent.query_decomposer._decompose_chain") as mock:
            mock.invoke.return_value = "not valid json"
            with pytest.raises(ValueError, match="Failed to decompose query"):
                decompose_query("schema", "question")

    def test_raises_value_error_when_llm_call_fails(self):
        with patch("spreadsheet_mcp_agent.query_decomposer._decompose_chain") as mock:
            mock.invoke.side_effect = RuntimeError("API error")
            with pytest.raises(ValueError, match="Failed to decompose query"):
                decompose_query("schema", "question")


# ---------------------------------------------------------------------------
# ExecuteHandler
# ---------------------------------------------------------------------------

class TestExecuteHandler:
    def test_success_sets_result_and_success_flag(self):
        data = _make_sales_context()
        ctx = SqlContext(
            schema="schema",
            sql="SELECT * FROM sales",
            execute_func=lambda s: data["sales"],
            data_context=data,
            question="q",
        )
        handler = ExecuteHandler()
        handler.set_next(ExhaustedHandler())
        result = handler.handle(ctx)
        assert result.success is True
        assert result.result is not None

    def test_failure_passes_to_next_immediately(self):
        """On first failure the handler should pass through, not retry."""
        call_count = [0]

        def counting_fail(sql):
            call_count[0] += 1
            raise Exception("SQL execution failed: forced")

        ctx = SqlContext(
            schema="schema",
            sql="BAD SQL",
            execute_func=counting_fail,
            data_context=_make_sales_context(),
            question="q",
        )
        exhausted = ExhaustedHandler()
        handler = ExecuteHandler()
        handler.set_next(exhausted)

        with pytest.raises(RuntimeError):
            handler.handle(ctx)

        # ExecuteHandler should only attempt once (no retries)
        assert call_count[0] == 1


# ---------------------------------------------------------------------------
# DecompositionHandler
# ---------------------------------------------------------------------------

class TestDecompositionHandler:
    def _make_ctx(self, question="complex question", data_context=None) -> SqlContext:
        return SqlContext(
            schema="schema",
            sql="INVALID SQL",
            execute_func=_always_fail,
            attempt=1,
            last_error="Parser error",
            data_context=data_context if data_context is not None else _make_sales_context(),
            question=question,
        )

    def test_executes_multi_step_plan_successfully(self):
        steps = [
            QueryStep(
                "step_totals",
                "SELECT region, SUM(revenue) AS total FROM sales GROUP BY region",
                "Aggregate",
            ),
            QueryStep(
                "step_ranked",
                "SELECT *, RANK() OVER (ORDER BY total DESC) AS rnk FROM step_totals",
                "Rank",
            ),
        ]
        handler = DecompositionHandler()
        handler.set_next(ExhaustedHandler())
        ctx = self._make_ctx()

        with patch("spreadsheet_mcp_agent.query_decomposer.decompose_query", return_value=steps):
            result = handler.handle(ctx)

        assert result.success is True
        assert result.was_decomposed is True
        assert result.sql == steps[-1].sql
        assert isinstance(result.result, pd.DataFrame)
        assert "rnk" in result.result.columns

    def test_passes_through_when_decomposition_llm_fails(self):
        handler = DecompositionHandler()
        handler.set_next(ExhaustedHandler())
        ctx = self._make_ctx()

        with patch(
            "spreadsheet_mcp_agent.query_decomposer.decompose_query",
            side_effect=ValueError("LLM failed"),
        ):
            with pytest.raises(RuntimeError, match="Query could not be answered"):
                handler.handle(ctx)

    def test_passes_through_when_a_step_fails_to_execute(self):
        steps = [
            QueryStep("step_bad", "SELECT nonexistent_col FROM sales", "bad"),
        ]
        handler = DecompositionHandler()
        handler.set_next(ExhaustedHandler())
        ctx = self._make_ctx()

        with patch("spreadsheet_mcp_agent.query_decomposer.decompose_query", return_value=steps):
            with pytest.raises(RuntimeError, match="Query could not be answered"):
                handler.handle(ctx)

    def test_skipped_when_data_context_is_none(self):
        handler = DecompositionHandler()
        handler.set_next(ExhaustedHandler())
        ctx = self._make_ctx(data_context=None)
        ctx.data_context = None

        with pytest.raises(RuntimeError, match="Query could not be answered"):
            handler.handle(ctx)

    def test_skipped_when_question_is_empty(self):
        handler = DecompositionHandler()
        handler.set_next(ExhaustedHandler())
        ctx = self._make_ctx(question="")

        with pytest.raises(RuntimeError, match="Query could not be answered"):
            handler.handle(ctx)

    def test_intermediate_steps_available_to_later_steps(self):
        """Each step's result must be accessible as a table by subsequent steps."""
        steps = [
            QueryStep("step_a", "SELECT region, SUM(revenue) AS total FROM sales GROUP BY region", "agg"),
            QueryStep("step_b", "SELECT COUNT(*) AS n FROM step_a", "count"),
        ]
        handler = DecompositionHandler()
        handler.set_next(ExhaustedHandler())
        ctx = self._make_ctx()

        with patch("spreadsheet_mcp_agent.query_decomposer.decompose_query", return_value=steps):
            result = handler.handle(ctx)

        assert result.success is True
        assert result.result["n"].iloc[0] == 2  # two distinct regions


# ---------------------------------------------------------------------------
# build_handler_chain — new chain shape
# ---------------------------------------------------------------------------

class TestBuildHandlerChain:
    def test_chain_is_execute_decompose_exhausted(self):
        chain = build_handler_chain()
        assert isinstance(chain, ExecuteHandler)
        assert isinstance(chain._next, DecompositionHandler)
        assert isinstance(chain._next._next, ExhaustedHandler)

    def test_no_correction_handler_in_chain(self):
        """CorrectionHandler must NOT appear in the new proactive chain."""
        from spreadsheet_mcp_agent import handlers as h
        assert not hasattr(h, "CorrectionHandler"), (
            "CorrectionHandler should have been removed from handlers.py"
        )


# ---------------------------------------------------------------------------
# retry_with_recovery — public API
# ---------------------------------------------------------------------------

class TestRetryWithRecovery:
    def test_direct_query_success_returns_was_decomposed_false(self):
        data = _make_sales_context()

        def execute_func(sql):
            import duckdb
            conn = duckdb.connect(":memory:")
            conn.register("sales", data["sales"])
            return conn.execute(sql).fetch_df()

        sql, result, was_decomposed = retry_with_recovery(
            schema="Table: sales",
            original_sql="SELECT * FROM sales",
            execute_func=execute_func,
            data_context=data,
            question="show all sales",
        )
        assert isinstance(result, pd.DataFrame)
        assert was_decomposed is False

    def test_decomposed_path_returns_was_decomposed_true(self):
        data = _make_sales_context()
        steps = [
            QueryStep(
                "step_totals",
                "SELECT region, SUM(revenue) AS total FROM sales GROUP BY region",
                "aggregate",
            ),
        ]

        with patch(
            "spreadsheet_mcp_agent.query_decomposer.decompose_query",
            return_value=steps,
        ):
            sql, result, was_decomposed = retry_with_recovery(
                schema="Table: sales",
                original_sql="INVALID SQL !!!",
                execute_func=_always_fail,
                data_context=data,
                question="show sales totals",
            )

        assert was_decomposed is True
        assert isinstance(result, pd.DataFrame)
        assert "total" in result.columns

    def test_raises_when_both_direct_and_decompose_fail(self):
        data = _make_sales_context()

        with patch(
            "spreadsheet_mcp_agent.query_decomposer.decompose_query",
            side_effect=ValueError("LLM unavailable"),
        ):
            with pytest.raises(RuntimeError, match="Query could not be answered"):
                retry_with_recovery(
                    schema="Table: sales",
                    original_sql="INVALID SQL",
                    execute_func=_always_fail,
                    data_context=data,
                    question="complex question",
                )
