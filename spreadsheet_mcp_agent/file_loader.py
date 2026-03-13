"""Backward-compatible shim. File loading is now handled by loaders.FileLoaderContext."""

import pandas as pd

from .loaders import FileLoaderContext

_context = FileLoaderContext()


def load_file(file_path: str) -> pd.DataFrame:
    """Load a CSV or Excel file. Delegates to FileLoaderContext (Strategy pattern)."""
    return _context.load(file_path)
