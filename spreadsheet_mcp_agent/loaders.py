"""Strategy pattern: file format loaders."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class FileLoaderStrategy(ABC):
    """Abstract strategy for loading a specific file format."""

    @abstractmethod
    def can_handle(self, extension: str) -> bool: ...

    @abstractmethod
    def load(self, file_path: str) -> pd.DataFrame: ...


class CsvLoaderStrategy(FileLoaderStrategy):
    def can_handle(self, extension: str) -> bool:
        return extension == ".csv"

    def load(self, file_path: str) -> pd.DataFrame:
        logger.info(f"Loading CSV: {file_path}")
        return pd.read_csv(file_path)


class ExcelLoaderStrategy(FileLoaderStrategy):
    def can_handle(self, extension: str) -> bool:
        return extension in (".xlsx", ".xls")

    def load(self, file_path: str) -> pd.DataFrame:
        logger.info(f"Loading Excel: {file_path}")
        return pd.read_excel(file_path)


class FileLoaderContext:
    """Context that selects the appropriate FileLoaderStrategy by file extension.

    To support a new format, add a new FileLoaderStrategy subclass and register
    it in _strategies — no other code needs to change.
    """

    _strategies: list[FileLoaderStrategy] = [
        CsvLoaderStrategy(),
        ExcelLoaderStrategy(),
    ]

    def load(self, file_path: str) -> pd.DataFrame:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()
        for strategy in self._strategies:
            if strategy.can_handle(ext):
                df = strategy.load(file_path)
                logger.info(f"Loaded file with shape {df.shape}")
                return df

        raise ValueError(
            f"Unsupported file format: {ext}. "
            f"Supported: {[s.__class__.__name__ for s in self._strategies]}"
        )
