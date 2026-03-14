"""MCP server: thin adapter that delegates to SpreadsheetQueryFacade."""

import json
import logging

from fastmcp import FastMCP

from .config import config
from .events import JsonlObserver, LoggingObserver, SqliteObserver
from .facade import SpreadsheetQueryFacade
from .multi_step_planner import MultiStepQueryPlanner

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
_planner = MultiStepQueryPlanner()


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


@mcp.tool()
def query_spreadsheet_complex(file_paths: list[str], question: str) -> str:
    """Query one or more spreadsheets with complex multi-step analytical questions.

    Automatically assesses whether the question requires multiple sequential
    SQL steps. If so, executes each step in order, making each step's result
    available as a named table for the next step.

    Args:
        file_paths: List of paths to CSV or Excel files. All files are loaded
                    into a shared DataContext so queries can JOIN across them.
        question: Natural language analytical question, including complex ones
                  involving window functions, MoM deltas, percentile rankings,
                  coefficient of variation, or composite scoring.

    Returns:
        JSON string with: success, complexity, steps_executed (list of step traces
        with sql/row_count/preview per step), final_result, generated_sql.
    """
    try:
        result = _planner.execute(file_paths, question)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.error(f"Complex query failed: {str(e)}", exc_info=True)
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
