"""Multi-step analytical query planner.

Decomposes complex analytical questions into sequential SQL steps where each
step's result DataFrame is accumulated into the DataContext, making it available
as a named table for all subsequent steps.

Flow:
  1. Load file(s) → DataContext
  2. Assess complexity via LLM → "simple" | "complex" + step plan JSON
  3a. If simple: delegate to existing single-query pipeline
  3b. If complex: iterate steps, accumulating DataContext between each
  4. Return full step trace + final result
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from .config import config
from .handlers import retry_with_recovery
from .llm_client import RetryDecorator, get_llm
from .loaders import DataContext, FileLoaderContext
from .schema_extractor import extract_schema
from .sql_executor import execute_sql
from .sql_generator import extract_sql_from_response, generate_sql

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class StepPlan:
    step: int
    description: str
    output_table: str


@dataclass
class StepTrace:
    step: int
    description: str
    output_table: str
    sql: str
    row_count: int
    column_count: int
    preview: list[dict]


@dataclass
class AssessmentResult:
    complexity: str          # "simple" | "complex"
    reason: str
    steps: list[StepPlan] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_ASSESSMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a senior data analyst and SQL architect.
Given the database schema and the user's question, decide whether this question
can be answered with a SINGLE SQL query or requires multiple sequential steps.

== SCHEMA ==
{schema}

== QUESTION ==
{question}

== RULES FOR CLASSIFICATION ==
Classify as "complex" when the question requires TWO OR MORE of:
  - Window functions computed over an intermediate aggregate (e.g., RANK over a per-group subtotal)
  - A self-join or cross-join on a derived result set
  - Percentile/quantile calculations over a filtered or grouped intermediate set
  - Month-over-month / period-over-period deltas where the lag itself is then filtered or ranked
  - A composite score built from independently computed metrics that must each be normalised first

Classify as "simple" for everything else — including questions that use a single
window function, a single aggregation, or a straightforward JOIN.

== ATOMICITY RULE FOR STEPS ==
Each step must represent exactly ONE conceptual transformation that a human SQL
expert could write as a single, clean CTE. Do not split trivially easy operations
into separate steps. Aim for the MINIMUM number of steps that avoids producing
invalid or unpredictably large SQL.

== OUTPUT FORMAT ==
Respond with ONLY valid JSON — no markdown, no prose:

{{
  "complexity": "simple",
  "reason": "<one sentence explanation>",
  "steps": []
}}

or

{{
  "complexity": "complex",
  "reason": "<one sentence explanation>",
  "steps": [
    {{
      "step": 1,
      "description": "<what this step computes, written for a SQL generator>",
      "output_table": "<snake_case_table_name>"
    }}
  ]
}}

The last step's output_table is the final answer the user sees.
If complexity is "simple", return an empty array for "steps"."""),
])

_STEP_SQL_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a SQL expert working on step {step_number} of a multi-step analytical query.

== FULL ACCUMULATED SCHEMA (ALL AVAILABLE TABLES) ==
{schema}

== AVAILABLE TABLE NAMES ==
{available_tables}

== OVERALL QUESTION BEING ANSWERED ==
{original_question}

== THIS STEP'S TASK ==
{step_description}

== OUTPUT TABLE NAME ==
Your SELECT statement will be stored as a new table named: {output_table}

Write a single SQL SELECT statement that computes what this step requires.
You may JOIN, filter, aggregate, or apply window functions over any of the
available tables listed above.

IMPORTANT:
- Do NOT use CREATE TABLE or INSERT — write only a SELECT statement.
- The result of this SELECT will automatically become the table "{output_table}" for subsequent steps.
- Output ONLY the raw SQL. No markdown, no code fences, no explanations."""),
])


# ---------------------------------------------------------------------------
# Assessment JSON parser
# ---------------------------------------------------------------------------

def _parse_assessment_json(raw: str) -> AssessmentResult:
    """Parse the LLM assessment response into an AssessmentResult."""
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Assessment LLM returned non-JSON: {raw[:200]}") from exc

    steps = [
        StepPlan(
            step=s["step"],
            description=s["description"],
            output_table=re.sub(r"[^a-zA-Z0-9_]", "_", s["output_table"]),
        )
        for s in payload.get("steps", [])
    ]
    return AssessmentResult(
        complexity=payload.get("complexity", "simple"),
        reason=payload.get("reason", ""),
        steps=steps,
    )


# ---------------------------------------------------------------------------
# Module-level LCEL chains (instantiated once, same pattern as sql_generator.py)
# ---------------------------------------------------------------------------

_assessment_chain = RetryDecorator(
    _ASSESSMENT_PROMPT
    | get_llm()
    | StrOutputParser()
    | RunnableLambda(_parse_assessment_json)
)

_step_sql_chain = RetryDecorator(
    _STEP_SQL_PROMPT
    | get_llm()
    | StrOutputParser()
    | RunnableLambda(extract_sql_from_response)
)


# ---------------------------------------------------------------------------
# MultiStepQueryPlanner
# ---------------------------------------------------------------------------

class MultiStepQueryPlanner:
    """Orchestrates multi-step analytical queries.

    Each call to execute() is stateless — it loads the file, assesses complexity,
    and either delegates to the simple path or runs the step accumulation loop.
    """

    def __init__(self) -> None:
        self._loader = FileLoaderContext()

    def execute(self, file_paths: list[str] | str, question: str) -> dict[str, Any]:
        """Run the query pipeline and return a JSON-serialisable result dict.

        Args:
            file_paths: One or more file paths. A list loads all files into a
                        shared DataContext so queries can JOIN across them.
                        A bare string is also accepted for backwards compatibility.
            question: Natural language analytical question.

        Returns keys:
            success, run_id, complexity, steps_executed, final_result, generated_sql
        """
        run_id = str(uuid.uuid4())
        # Normalise to comma-separated string that FileLoaderContext expects
        if isinstance(file_paths, list):
            file_path_str = ",".join(file_paths)
        else:
            file_path_str = file_paths
        logger.info(f"[{run_id}] MultiStepQueryPlanner.execute — files={file_path_str}")

        data_context: DataContext = self._loader.load(file_path_str)
        schema = extract_schema(data_context)
        assessment = self._assess(schema, question, run_id)

        if assessment.complexity == "simple" or not assessment.steps:
            if assessment.complexity == "complex":
                logger.warning(f"[{run_id}] complex with no steps — falling back to simple")
            return self._run_simple(data_context, schema, question, run_id, assessment.complexity)

        return self._run_steps(data_context, assessment, question, run_id)

    # ------------------------------------------------------------------
    # Simple-path fallthrough
    # ------------------------------------------------------------------

    def _run_simple(
        self,
        data_context: DataContext,
        schema: str,
        question: str,
        run_id: str,
        complexity: str = "simple",
    ) -> dict[str, Any]:
        logger.info(f"[{run_id}] Complexity={complexity} — using single-query path")
        sql = generate_sql(schema, question)

        def _exec(s: str) -> pd.DataFrame:
            return execute_sql(data_context, s)

        final_sql, result_df = retry_with_recovery(
            schema, sql, _exec, max_retries=config.MAX_SQL_RETRIES
        )
        preview = result_df.head(config.MAX_RESULT_ROWS).to_dict(orient="records")
        trace = StepTrace(
            step=1,
            description=question,
            output_table="result",
            sql=final_sql,
            row_count=len(result_df),
            column_count=len(result_df.columns),
            preview=preview,
        )
        return self._format_output(complexity, [trace], run_id)

    # ------------------------------------------------------------------
    # Multi-step execution loop
    # ------------------------------------------------------------------

    def _run_steps(
        self,
        data_context: DataContext,
        assessment: AssessmentResult,
        original_question: str,
        run_id: str,
    ) -> dict[str, Any]:
        original_tables = set(data_context.keys())
        completed_traces: list[StepTrace] = []
        total_steps = len(assessment.steps)

        for step_plan in assessment.steps:
            step_num = step_plan.step
            is_last = step_num == total_steps
            logger.info(
                f"[{run_id}] Step {step_num}/{total_steps}: {step_plan.description[:80]}"
            )

            # Guard: output_table must not shadow an original table
            if step_plan.output_table in original_tables:
                raise RuntimeError(
                    f"Step {step_num} output_table '{step_plan.output_table}' collides "
                    f"with an original loaded table. Aborting to prevent data corruption."
                )

            current_schema = extract_schema(data_context)
            available_tables = list(data_context.keys())

            try:
                sql = _step_sql_chain.invoke({
                    "step_number": step_num,
                    "schema": current_schema,
                    "available_tables": "\n".join(f"  - {t}" for t in available_tables),
                    "original_question": original_question,
                    "step_description": step_plan.description,
                    "output_table": step_plan.output_table,
                })
            except Exception as exc:
                raise RuntimeError(
                    f"Step {step_num} SQL generation failed. "
                    f"Completed: {[t.output_table for t in completed_traces]}. "
                    f"Error: {exc}"
                ) from exc

            def _exec(s: str, _ctx=data_context) -> pd.DataFrame:
                return execute_sql(_ctx, s)

            try:
                final_sql, result_df = retry_with_recovery(
                    current_schema, sql, _exec, max_retries=config.MAX_SQL_RETRIES
                )
            except Exception as exc:
                completed_summaries = [
                    f"step {t.step} ({t.output_table}): {t.row_count} rows"
                    for t in completed_traces
                ]
                raise RuntimeError(
                    f"Step {step_num} ('{step_plan.description}') failed after "
                    f"{config.MAX_SQL_RETRIES} retries.\n"
                    f"Completed: {completed_summaries}\n"
                    f"Failed SQL: {sql}\n"
                    f"Error: {exc}"
                ) from exc

            # Accumulate into DataContext — key mechanism enabling subsequent steps
            data_context[step_plan.output_table] = result_df
            logger.info(
                f"[{run_id}] Step {step_num} done — "
                f"'{step_plan.output_table}' shape={result_df.shape}"
            )

            preview_limit = config.MAX_RESULT_ROWS if is_last else config.MAX_SAMPLE_ROWS
            preview = result_df.head(preview_limit).to_dict(orient="records")
            completed_traces.append(StepTrace(
                step=step_num,
                description=step_plan.description,
                output_table=step_plan.output_table,
                sql=final_sql,
                row_count=len(result_df),
                column_count=len(result_df.columns),
                preview=preview,
            ))

        return self._format_output("complex", completed_traces, run_id)

    # ------------------------------------------------------------------
    # Complexity assessment
    # ------------------------------------------------------------------

    def _assess(self, schema: str, question: str, run_id: str) -> AssessmentResult:
        logger.info(f"[{run_id}] Assessing query complexity")
        try:
            result = _assessment_chain.invoke({"schema": schema, "question": question})
            logger.info(
                f"[{run_id}] Assessment: complexity={result.complexity}, "
                f"steps={len(result.steps)}, reason={result.reason}"
            )
            return result
        except Exception as exc:
            logger.warning(
                f"[{run_id}] Assessment failed ({exc}) — falling back to simple"
            )
            return AssessmentResult(complexity="simple", reason="assessment_failed")

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_output(
        complexity: str,
        steps_executed: list[StepTrace],
        run_id: str,
    ) -> dict[str, Any]:
        last = steps_executed[-1]
        step_dicts = [
            {
                "step": t.step,
                "description": t.description,
                "output_table": t.output_table,
                "sql": t.sql,
                "row_count": t.row_count,
                "column_count": t.column_count,
                "preview": t.preview,
            }
            for t in steps_executed
        ]
        return {
            "success": True,
            "run_id": run_id,
            "complexity": complexity,
            "steps_executed": step_dicts,
            "final_result": {
                "output_table": last.output_table,
                "row_count": last.row_count,
                "column_count": last.column_count,
                "preview": last.preview,
            },
            "generated_sql": last.sql,
        }
