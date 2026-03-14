"""SQL query execution on DataFrames using DuckDB."""

import logging

import duckdb
import pandas as pd

from .loaders import DataContext

logger = logging.getLogger(__name__)


def execute_sql(data_context: DataContext, sql: str) -> pd.DataFrame:
    """Execute SQL query against a DataContext using DuckDB.

    Each key in *data_context* is registered as a DuckDB table with that name,
    allowing the SQL to reference any table (or JOIN across tables).

    Args:
        data_context: Dict mapping table names to DataFrames.
        sql: SQL query to execute.

    Returns:
        Result DataFrame.

    Raises:
        Exception: If SQL execution fails.
    """
    logger.info(f"Executing SQL: {sql[:100]}...")

    try:
        conn = duckdb.connect(":memory:")
        for table_name, df in data_context.items():
            conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM df')

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


def validate_sql(data_context: DataContext, sql: str) -> bool:
    """Validate SQL query syntax without executing it.

    Args:
        data_context: Dict mapping table names to DataFrames.
        sql: SQL query to validate.

    Returns:
        True if SQL is valid.

    Raises:
        Exception: If SQL is invalid.
    """
    try:
        conn = duckdb.connect(":memory:")
        for table_name, df in data_context.items():
            conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM df')
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
