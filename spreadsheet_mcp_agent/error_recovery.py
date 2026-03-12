"""Error recovery and retry logic for SQL generation and execution."""

import logging

from .llm_client import generate_text
from .sql_generator import extract_sql_from_response

logger = logging.getLogger(__name__)


def recover_from_sql_error(
    schema: str, original_sql: str, error_message: str, max_retries: int = 3
) -> str:
    """Attempt to recover from SQL execution error by asking LLM to fix it.

    Args:
        schema: DataFrame schema information.
        original_sql: The original SQL query that failed.
        error_message: The error message from execution.
        max_retries: Maximum number of retry attempts.

    Returns:
        Corrected SQL query string.

    Raises:
        RuntimeError: If all retry attempts fail.
    """
    logger.warning(f"Attempting to recover from SQL error. Max retries: {max_retries}")

    for attempt in range(max_retries):
        try:
            logger.info(f"Recovery attempt {attempt + 1}/{max_retries}")

            prompt = f"""You are a SQL expert. The following SQL query produced an error:

Schema:
{schema}

Original SQL:
{original_sql}

Error:
{error_message}

Please provide a corrected SQL query that fixes this error. Output ONLY the SQL query, no explanations or markdown."""

            response = generate_text(prompt)
            corrected_sql = extract_sql_from_response(response)

            logger.info(f"Generated corrected SQL: {corrected_sql[:100]}...")
            return corrected_sql

        except Exception as e:
            logger.error(f"Recovery attempt {attempt + 1} failed: {str(e)}")

            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Failed to recover from SQL error after {max_retries} attempts. "
                    f"Last error: {str(e)}"
                ) from e

    raise RuntimeError("SQL recovery failed: unknown error")


def retry_with_recovery(
    schema: str,
    original_sql: str,
    execute_func,
    max_retries: int = 3,
) -> tuple[str, any]:
    """Execute SQL with automatic error recovery and retries.

    Args:
        schema: DataFrame schema information.
        original_sql: The original SQL query.
        execute_func: Function to execute SQL (should take sql string as argument).
        max_retries: Maximum retry attempts.

    Returns:
        Tuple of (final_sql, result).

    Raises:
        RuntimeError: If all attempts fail.
    """
    current_sql = original_sql

    for attempt in range(max_retries):
        try:
            logger.info(f"Execution attempt {attempt + 1}/{max_retries}")
            result = execute_func(current_sql)
            logger.info("Execution successful")
            return current_sql, result

        except Exception as e:
            logger.error(f"Execution attempt {attempt + 1} failed: {str(e)}")

            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"SQL execution failed after {max_retries} attempts. "
                    f"Last error: {str(e)}"
                ) from e

            # Try to recover
            try:
                current_sql = recover_from_sql_error(
                    schema, current_sql, str(e), max_retries=1
                )

            except RuntimeError as recovery_error:
                logger.error(f"Recovery failed: {str(recovery_error)}")
                raise RuntimeError(
                    f"Execution failed and recovery was not possible: {str(e)}"
                ) from e

    raise RuntimeError("SQL execution with recovery failed: unknown error")
