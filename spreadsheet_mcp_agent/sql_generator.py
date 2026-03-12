"""SQL query generation using LLM."""

import logging
import re

from .llm_client import generate_text

logger = logging.getLogger(__name__)


def generate_sql(schema: str, question: str) -> str:
    """Generate SQL query from natural language question.

    Args:
        schema: Schema string describing the table structure.
        question: Natural language question to convert to SQL.

    Returns:
        Generated SQL query string.

    Raises:
        ValueError: If LLM fails to generate valid SQL.
    """
    prompt = f"""You are a SQL expert. Generate a SQL query based on the following:

A table named 'data' exists with the following schema:

{schema}

User question: {question}

IMPORTANT: Output ONLY the SQL query. No markdown, no explanations, no code blocks. Just the raw SQL query."""

    logger.info(f"Generating SQL for question: {question[:50]}...")

    try:
        response = generate_text(prompt)

        # Clean up response - remove markdown code blocks if present
        sql = response.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]

        sql = sql.strip()

        logger.info(f"Generated SQL: {sql[:100]}...")
        return sql

    except Exception as e:
        logger.error(f"SQL generation failed: {str(e)}")
        raise ValueError(f"Failed to generate SQL: {str(e)}") from e


def extract_sql_from_response(response: str) -> str:
    """Extract SQL query from LLM response, removing markdown if present.

    Args:
        response: Raw LLM response.

    Returns:
        Cleaned SQL query string.
    """
    sql = response.strip()

    # Remove markdown code blocks
    if sql.startswith("```sql"):
        sql = sql[6:]
    elif sql.startswith("```"):
        sql = sql[3:]

    if sql.endswith("```"):
        sql = sql[:-3]

    return sql.strip()
