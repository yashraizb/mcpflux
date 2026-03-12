"""Schema extraction utilities for DataFrames."""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def extract_schema(df: pd.DataFrame) -> str:
    """Extract schema information from a DataFrame.

    Args:
        df: Input DataFrame.

    Returns:
        Formatted schema string suitable for LLM prompts.
    """
    logger.info("Extracting schema from DataFrame")

    # Column information
    column_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        column_info.append(f"  - {col}: {dtype}")

    columns_section = "\n".join(column_info)

    # Sample data (first 5 rows)
    sample_rows = df.head(5)
    sample_data = sample_rows.to_string(index=False)

    # Row count
    row_count = len(df)

    schema = f"""Table: data
Columns:
{columns_section}

Row count: {row_count}

Sample data:
{sample_data}"""

    logger.info(f"Schema extracted: {len(schema)} characters")
    return schema


def get_column_names(df: pd.DataFrame) -> list[str]:
    """Get list of column names from DataFrame.

    Args:
        df: Input DataFrame.

    Returns:
        List of column names.
    """
    return df.columns.tolist()


def get_column_types(df: pd.DataFrame) -> dict[str, str]:
    """Get dictionary of column names to data types.

    Args:
        df: Input DataFrame.

    Returns:
        Dictionary mapping column names to data types.
    """
    return {col: str(df[col].dtype) for col in df.columns}


def get_row_count(df: pd.DataFrame) -> int:
    """Get number of rows in DataFrame.

    Args:
        df: Input DataFrame.

    Returns:
        Number of rows.
    """
    return len(df)
