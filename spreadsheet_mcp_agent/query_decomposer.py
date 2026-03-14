"""Query decomposition: breaks complex analytical questions into sequential SQL steps.

When a direct single SQL query fails (e.g. for complex multi-step analytics with
window functions, cross-joins, derived metrics), this module asks the LLM to
decompose the question into a series of simple, focused sub-queries.  Each step
produces a named intermediate result that subsequent steps can reference as a
regular table.
"""

import json
import logging
from dataclasses import dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .llm_client import RetryDecorator, get_llm

logger = logging.getLogger(__name__)

_DECOMPOSE_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a SQL expert. A direct SQL query for the following question failed because it is too complex.

Schema:
{schema}

Question: {question}

Break this into a sequence of simple, focused SQL steps where each step builds on the previous ones.

Return ONLY a valid JSON array (no markdown, no explanations). Each element must have:
- "step_name": a short SQL identifier for the intermediate result (e.g. "step_monthly_totals")
- "sql": the SQL SELECT statement for this step
- "description": a brief description of what this step computes

Rules:
- step_name must be a valid SQL identifier (lowercase letters, digits, underscores only)
- Each step must be a SELECT statement
- Later steps may reference earlier step_names as table names
- The final step must fully answer the original question

Example output:
[
  {{"step_name": "step_monthly_totals", "sql": "SELECT month, SUM(revenue) AS total FROM sales GROUP BY month", "description": "Aggregate monthly revenue"}},
  {{"step_name": "step_ranked", "sql": "SELECT *, RANK() OVER (ORDER BY total DESC) AS rnk FROM step_monthly_totals", "description": "Rank months by revenue"}}
]"""),
])

_decompose_chain = RetryDecorator(
    _DECOMPOSE_PROMPT
    | get_llm()
    | StrOutputParser()
)


@dataclass
class QueryStep:
    """A single step in a decomposed multi-step query plan."""

    step_name: str
    sql: str
    description: str


def _parse_steps(response: str) -> list[QueryStep]:
    """Parse the LLM JSON response into an ordered list of QueryStep objects.

    Raises:
        ValueError: If the response is not a valid non-empty JSON array of steps.
    """
    text = response.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    steps_data = json.loads(text)
    if not isinstance(steps_data, list) or len(steps_data) == 0:
        raise ValueError("Decomposition response must be a non-empty JSON array")

    steps: list[QueryStep] = []
    for item in steps_data:
        if not all(k in item for k in ("step_name", "sql", "description")):
            raise ValueError(f"Step is missing required fields: {item}")
        steps.append(QueryStep(
            step_name=str(item["step_name"]),
            sql=str(item["sql"]),
            description=str(item["description"]),
        ))
    return steps


def decompose_query(schema: str, question: str) -> list[QueryStep]:
    """Break a complex analytical question into sequential SQL steps.

    Sends the schema and question to the LLM and parses the returned JSON plan
    into an ordered list of :class:`QueryStep` objects.  Steps are ordered so
    that each step may reference the ``step_name`` of any earlier step as a
    table name.

    Args:
        schema: Schema string describing the available tables.
        question: Complex analytical question that could not be answered directly.

    Returns:
        Ordered list of QueryStep objects to execute sequentially.

    Raises:
        ValueError: If the LLM call fails or its response cannot be parsed.
    """
    logger.info(f"Decomposing complex query: {question[:80]}...")
    try:
        response = _decompose_chain.invoke({"schema": schema, "question": question})
        steps = _parse_steps(response)
        logger.info(
            f"Query decomposed into {len(steps)} steps: "
            f"{[s.step_name for s in steps]}"
        )
        return steps
    except Exception as e:
        logger.error(f"Query decomposition failed: {e}")
        raise ValueError(f"Failed to decompose query: {e}") from e
