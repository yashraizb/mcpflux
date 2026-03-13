"""SQL query generation using LangChain LCEL chain + LLM provider strategy."""

import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from .llm_client import RetryDecorator, get_llm

logger = logging.getLogger(__name__)

_SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a SQL expert. Generate a SQL query based on the following:

The following tables are available:

{schema}

User question: {question}

IMPORTANT: Output ONLY the SQL query. No markdown, no explanations, no code blocks. Just the raw SQL query."""),
])


def extract_sql_from_response(response: str) -> str:
    """Remove markdown code fences from LLM response."""
    sql = response.strip()
    if sql.startswith("```sql"):
        sql = sql[6:]
    elif sql.startswith("```"):
        sql = sql[3:]
    if sql.endswith("```"):
        sql = sql[:-3]
    return sql.strip()


# LCEL chain wrapped in RetryDecorator (Decorator pattern)
# get_llm() returns the runnable from whichever provider is configured (Strategy pattern)
_sql_chain = RetryDecorator(
    _SQL_GENERATION_PROMPT
    | get_llm()
    | StrOutputParser()
    | RunnableLambda(extract_sql_from_response)
)


def generate_sql(schema: str, question: str) -> str:
    """Generate SQL from a natural language question.

    Args:
        schema: Schema string describing the table structure.
        question: Natural language question to convert to SQL.

    Returns:
        Generated SQL query string.

    Raises:
        ValueError: If LLM fails to generate SQL.
    """
    logger.info(f"Generating SQL for question: {question[:50]}...")
    try:
        sql = _sql_chain.invoke({"schema": schema, "question": question})
        logger.info(f"Generated SQL: {sql[:100]}...")
        return sql
    except Exception as e:
        logger.error(f"SQL generation failed: {str(e)}")
        raise ValueError(f"Failed to generate SQL: {str(e)}") from e
