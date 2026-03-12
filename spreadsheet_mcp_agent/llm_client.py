"""LLM client for generating SQL queries."""

import logging
from typing import Optional

from anthropic import Anthropic

from .config import config

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for Anthropic API calls."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize LLM client.

        Args:
            api_key: Anthropic API key. Defaults to config.ANTHROPIC_API_KEY.
            model: Model name. Defaults to config.MODEL_NAME.
        """
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        self.model = model or config.MODEL_NAME
        self.client = Anthropic(api_key=self.api_key)

    def generate_text(self, prompt: str) -> str:
        """Generate text using Anthropic API.

        Args:
            prompt: The prompt to send to the model.

        Returns:
            Generated text response.

        Raises:
            RuntimeError: If API call fails.
        """
        try:
            logger.info(f"Calling {self.model} with prompt of length {len(prompt)}")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            result = response.content[0].text
            logger.info("LLM generation successful")
            return result

        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise RuntimeError(f"LLM generation failed: {str(e)}") from e


def generate_text(prompt: str) -> str:
    """Convenience function to generate text using default LLM client.

    Args:
        prompt: The prompt to send to the model.

    Returns:
        Generated text response.
    """
    client = LLMClient()
    return client.generate_text(prompt)
