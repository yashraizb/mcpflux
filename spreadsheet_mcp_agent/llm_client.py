"""LLM client: RetryDecorator (Decorator pattern) + provider delegation."""

import logging
import time
from typing import Any, Optional

import anthropic
from langchain_core.runnables import Runnable

from .providers import LLMProvider, get_provider

logger = logging.getLogger(__name__)


class RetryDecorator(Runnable):
    """Decorator pattern: wraps any LangChain Runnable with exponential-backoff
    retry logic on HTTP 529 (API overloaded). Transparent to callers — exposes
    the same .invoke() interface as the wrapped Runnable.
    """

    def __init__(self, runnable: Runnable, max_retries: int = 3):
        self._runnable = runnable
        self._max_retries = max_retries

    def invoke(self, inputs: Any, config: Optional[Any] = None) -> Any:
        for attempt in range(self._max_retries):
            try:
                return self._runnable.invoke(inputs, config)
            except anthropic.APIStatusError as e:
                if e.status_code == 529 and attempt < self._max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        f"API overloaded (529), retrying in {wait}s... "
                        f"({attempt + 1}/{self._max_retries})"
                    )
                    time.sleep(wait)
                else:
                    raise


def get_llm() -> Any:
    """Return the LangChain Runnable from the configured LLM provider."""
    return get_provider().get_runnable()


def invoke_with_retry(chain: Runnable, inputs: Any, max_retries: int = 3) -> Any:
    """Convenience wrapper: invoke chain with 529 retry. Delegates to RetryDecorator."""
    return RetryDecorator(chain, max_retries=max_retries).invoke(inputs)


def generate_text(prompt: str) -> str:
    """Generate text from a plain string prompt using the configured provider."""
    provider: LLMProvider = get_provider()
    result = provider.generate(prompt)
    logger.info("LLM generation successful")
    return result
