"""File loading utilities for CSV and Excel files."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load_file(file_path: str) -> pd.DataFrame:
    """Load CSV or Excel file into a pandas DataFrame.

    Args:
        file_path: Path to the CSV or Excel file.

    Returns:
        Loaded DataFrame.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file format is not supported.
        Exception: If file cannot be read.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_suffix = path.suffix.lower()

    try:
        if file_suffix == ".csv":
            logger.info(f"Loading CSV file: {file_path}")
            df = pd.read_csv(file_path)

        elif file_suffix in [".xlsx", ".xls"]:
            logger.info(f"Loading Excel file: {file_path}")
            df = pd.read_excel(file_path)

        else:
            raise ValueError(
                f"Unsupported file format: {file_suffix}. "
                f"Supported formats: .csv, .xlsx, .xls"
            )

        logger.info(f"Successfully loaded file with shape {df.shape}")
        return df

    except (FileNotFoundError, ValueError):
        raise

    except Exception as e:
        logger.error(f"Error loading file {file_path}: {str(e)}")
        raise Exception(f"Failed to load file: {str(e)}") from e
