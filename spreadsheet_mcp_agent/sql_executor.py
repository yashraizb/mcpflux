"""SQL query execution on DataFrames using DuckDB."""

import logging
from typing import Any

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


def execute_sql(df: pd.DataFrame, sql: str) -> pd.DataFrame:
    """Execute SQL query on a DataFrame using DuckDB.

    Args:
        df: Input DataFrame to query.
        sql: SQL query to execute.

    Returns:
        Result DataFrame.

    Raises:
        Exception: If SQL execution fails.
    """
    logger.info(f"Executing SQL: {sql[:100]}...")

    try:
        # Create DuckDB connection
        conn = duckdb.connect(":memory:")

        # Register DataFrame as table
        conn.register("data", df)

        # Execute query
        result = conn.execute(sql).fetch_df()

        logger.info(f"Query executed successfully. Result shape: {result.shape}")
        return result

    except Exception as e:
        logger.error(f"SQL execution failed: {str(e)}")
        raise Exception(f"SQL execution failed: {str(e)}") from e

    finally:
        try:
            conn.close()
        except Exception:
            pass


def validate_sql(sql: str) -> bool:
    """Validate SQL query syntax without executing it.

    Args:
        sql: SQL query to validate.

    Returns:
        True if SQL is valid.

    Raises:
        Exception: If SQL is invalid.
    """
    try:
        conn = duckdb.connect(":memory:")
        conn.execute(f"EXPLAIN {sql}")
        return True

    except Exception as e:
        logger.error(f"SQL validation failed: {str(e)}")
        raise Exception(f"Invalid SQL: {str(e)}") from e

    finally:
        try:
            conn.close()
        except Exception:
            pass
