"""MCP server: thin adapter that delegates to SpreadsheetQueryFacade."""

import json
import logging

from fastmcp import FastMCP

from .config import config
from .events import JsonlObserver, LoggingObserver, SqliteObserver
from .facade import SpreadsheetQueryFacade

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("Spreadsheet Query Agent")
_facade = SpreadsheetQueryFacade(observers=[
    LoggingObserver(),
    JsonlObserver(config.EVENTS_LOG_PATH or None),
    SqliteObserver(config.METRICS_DB_PATH or None),
])


@mcp.tool()
def query_spreadsheet(file_path: str, question: str) -> str:
    """Query a spreadsheet with a natural language question.

    Args:
        file_path: Path to CSV or Excel file.
        question: Natural language question about the data.

    Returns:
        JSON string with generated_sql, result_preview, and row_count.
    """
    try:
        result = _facade.execute(file_path, question)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        return json.dumps({"success": False, "error": str(e), "error_type": type(e).__name__}, indent=2)


def run_server() -> None:
    """Validate config and start the MCP server."""
    try:
        config.validate()
        logger.info(f"Starting MCP server — provider={config.LLM_PROVIDER}, model={config.MODEL_NAME}")
        mcp.run()
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise
