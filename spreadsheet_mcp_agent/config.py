"""Configuration settings for the MCP server."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Configuration container for MCP server."""

    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")  # "anthropic" | "openai"
    MODEL_NAME: str = os.getenv("MODEL_NAME", "claude-haiku-4-5")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Observability
    EVENTS_LOG_PATH: str = os.getenv("EVENTS_LOG_PATH", "")   # default: ~/.mcpflux/events.jsonl
    METRICS_DB_PATH: str = os.getenv("METRICS_DB_PATH", "")   # default: ~/.mcpflux/metrics.db

    # SQL Execution Configuration
    MAX_SQL_RETRIES: int = 3
    MAX_SAMPLE_ROWS: int = 5
    MAX_RESULT_ROWS: int = 100

    # Validation
    ALLOWED_FILE_FORMATS: list[str] = None

    def __post_init__(self) -> None:
        """Initialize configuration."""
        if self.ALLOWED_FILE_FORMATS is None:
            self.ALLOWED_FILE_FORMATS = [".csv", ".xlsx", ".xls"]

    def validate(self) -> None:
        """Validate that required configuration is set."""
        if not self.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it before starting the server."
            )


# Global config instance
config = Config()
