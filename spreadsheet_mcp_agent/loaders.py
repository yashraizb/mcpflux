"""Strategy pattern: file format loaders."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# DataContext maps table names to DataFrames.
# Single CSV       → { "<stem>": df }
# Excel 1 sheet    → { "<stem>": df }
# Excel N sheets   → { "<stem>__<sheet_name>": df, ... }
# Multiple files   → merged dict from all files
DataContext = dict[str, pd.DataFrame]


class FileLoaderStrategy(ABC):
    """Abstract strategy for loading a specific file format."""

    @abstractmethod
    def can_handle(self, extension: str) -> bool: ...

    @abstractmethod
    def load(self, file_path: str) -> DataContext: ...


class CsvLoaderStrategy(FileLoaderStrategy):
    def can_handle(self, extension: str) -> bool:
        return extension == ".csv"

    def load(self, file_path: str) -> DataContext:
        logger.info(f"Loading CSV: {file_path}")
        stem = Path(file_path).stem
        df = pd.read_csv(file_path)
        return {stem: df}


class ExcelLoaderStrategy(FileLoaderStrategy):
    def can_handle(self, extension: str) -> bool:
        return extension in (".xlsx", ".xls")

    def load(self, file_path: str) -> DataContext:
        logger.info(f"Loading Excel: {file_path}")
        stem = Path(file_path).stem
        sheets: dict[str, pd.DataFrame] = pd.read_excel(file_path, sheet_name=None)
        if len(sheets) == 1:
            # Single-sheet workbook: use plain stem as table name
            df = next(iter(sheets.values()))
            return {stem: df}
        # Multi-sheet workbook: qualify each table as "<stem>__<sheet_name>"
        return {f"{stem}__{sheet_name}": df for sheet_name, df in sheets.items()}


class FileLoaderContext:
    """Context that selects the appropriate FileLoaderStrategy by file extension.

    Accepts one or more file paths separated by commas. All resulting DataContexts
    are merged so callers can JOIN across files and sheets.

    To support a new format, add a new FileLoaderStrategy subclass and register
    it in _strategies — no other code needs to change.
    """

    _strategies: list[FileLoaderStrategy] = [
        CsvLoaderStrategy(),
        ExcelLoaderStrategy(),
    ]

    def load(self, file_path: str) -> DataContext:
        """Load one or more files and return a merged DataContext.

        Args:
            file_path: Path to a CSV or Excel file, or multiple paths separated
                       by commas for cross-file queries.

        Returns:
            DataContext mapping table names to DataFrames.
        """
        paths = [p.strip() for p in file_path.split(",") if p.strip()]
        merged: DataContext = {}
        for p in paths:
            merged.update(self._load_single(p))
        logger.info(f"DataContext ready: {len(merged)} table(s) — {list(merged.keys())}")
        return merged

    def _load_single(self, file_path: str) -> DataContext:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()
        for strategy in self._strategies:
            if strategy.can_handle(ext):
                data_context = strategy.load(file_path)
                for name, df in data_context.items():
                    logger.info(f"Loaded table '{name}' with shape {df.shape}")
                return data_context

        raise ValueError(
            f"Unsupported file format: {ext}. "
            f"Supported: {[s.__class__.__name__ for s in self._strategies]}"
        )
