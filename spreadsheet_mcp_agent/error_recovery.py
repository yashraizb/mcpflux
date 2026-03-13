"""Backward-compatible shim. SQL error recovery is now handled by handlers.py."""

from .handlers import retry_with_recovery

__all__ = ["retry_with_recovery"]
