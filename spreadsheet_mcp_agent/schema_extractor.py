"""Schema extraction utilities for DataFrames."""

import logging

import pandas as pd

from .loaders import DataContext

logger = logging.getLogger(__name__)


def extract_schema(data_context: DataContext) -> str:
    """Extract schema information from a DataContext (one or more named DataFrames).

    Args:
        data_context: Dict mapping table names to DataFrames.

    Returns:
        Formatted schema string suitable for LLM prompts.
    """
    logger.info(f"Extracting schema from {len(data_context)} table(s)")

    sections = []
    for table_name, df in data_context.items():
        column_info = [f"  - {col}: {df[col].dtype}" for col in df.columns]
        columns_section = "\n".join(column_info)
        sample_data = df.head(5).to_string(index=False)

        section = f"""Table: {table_name}
Columns:
{columns_section}

Row count: {len(df)}

Sample data:
{sample_data}"""
        sections.append(section)

    schema = "\n\n---\n\n".join(sections)
    logger.info(f"Schema extracted: {len(schema)} characters")
    return schema
