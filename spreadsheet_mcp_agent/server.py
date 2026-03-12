"""Main MCP server implementation."""

import json
import logging
from typing import Any

from fastmcp import FastMCP

from .config import config
from .error_recovery import retry_with_recovery
from .file_loader import load_file
from .schema_extractor import extract_schema
from .sql_executor import execute_sql
from .sql_generator import generate_sql

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Spreadsheet Query Agent")


@mcp.tool()
def query_spreadsheet(file_path: str, question: str) -> str:
    """Query a spreadsheet with a natural language question.

    This tool orchestrates the entire pipeline:
    1. Load the file (CSV or Excel)
    2. Extract schema information
    3. Generate SQL from the question
    4. Execute the SQL query
    5. Return results

    Args:
        file_path: Path to CSV or Excel file.
        question: Natural language question about the data.

    Returns:
        JSON string with generated_sql, result_preview, and row_count.

    Raises:
        ValueError: If processing fails at any stage.
    """
    try:
        logger.info(f"Processing query: {question}")
        logger.info(f"File path: {file_path}")

        # Step 1: Load file
        logger.info("Step 1: Loading file")
        df = load_file(file_path)

        # Step 2: Extract schema
        logger.info("Step 2: Extracting schema")
        schema = extract_schema(df)

        # Step 3: Generate SQL
        logger.info("Step 3: Generating SQL")
        generated_sql = generate_sql(schema, question)

        # Step 4: Execute SQL with error recovery
        logger.info("Step 4: Executing SQL")

        def execute_func(sql: str) -> Any:
            return execute_sql(df, sql)

        final_sql, result_df = retry_with_recovery(
            schema, generated_sql, execute_func, max_retries=config.MAX_SQL_RETRIES
        )

        # Step 5: Format results
        logger.info("Step 5: Formatting results")

        # Get first N rows for preview
        preview_rows = result_df.head(config.MAX_RESULT_ROWS)
        preview = preview_rows.to_dict(orient="records")

        response = {
            "success": True,
            "generated_sql": final_sql,
            "result_preview": preview,
            "row_count": len(result_df),
            "total_columns": len(result_df.columns),
        }

        logger.info(f"Query successful. Returned {len(result_df)} rows")
        return json.dumps(response, indent=2, default=str)

    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        error_response = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }
        return json.dumps(error_response, indent=2)


def run_server() -> None:
    """Run the MCP server.

    This starts the server in stdio mode for integration with Claude Desktop.
    """
    try:
        config.validate()
        logger.info("Configuration validated")
        logger.info(f"Starting MCP server with model: {config.MODEL_NAME}")
        mcp.run()

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise

    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    run_server()
