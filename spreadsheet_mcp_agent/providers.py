"""Strategy pattern: LLM provider abstraction.

To add a new provider:
1. Subclass LLMProvider
2. Implement generate() and get_runnable()
3. Add a branch in get_provider()
4. Set LLM_PROVIDER=<name> in .env
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from .config import config

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Strategy interface for LLM vendor integrations."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send a plain-text prompt and return the response text."""
        ...

    @abstractmethod
    def get_runnable(self) -> Any:
        """Return a LangChain Runnable (chat model) for use in LCEL chains."""
        ...


class AnthropicProvider(LLMProvider):
    """Anthropic Claude via langchain-anthropic."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 1024):
        from langchain_anthropic import ChatAnthropic
        self._llm = ChatAnthropic(model=model, api_key=api_key, max_tokens=max_tokens)
        logger.info(f"AnthropicProvider initialised with model={model}")

    def generate(self, prompt: str) -> str:
        from langchain_core.messages import HumanMessage
        from langchain_core.output_parsers import StrOutputParser
        return (self._llm | StrOutputParser()).invoke([HumanMessage(content=prompt)])

    def get_runnable(self) -> Any:
        return self._llm


class OpenAIProvider(LLMProvider):
    """OpenAI GPT via langchain-openai."""

    def __init__(self, api_key: str, model: str = "gpt-4o", max_tokens: int = 1024):
        from langchain_openai import ChatOpenAI
        self._llm = ChatOpenAI(model=model, api_key=api_key, max_tokens=max_tokens)
        logger.info(f"OpenAIProvider initialised with model={model}")

    def generate(self, prompt: str) -> str:
        from langchain_core.messages import HumanMessage
        from langchain_core.output_parsers import StrOutputParser
        return (self._llm | StrOutputParser()).invoke([HumanMessage(content=prompt)])

    def get_runnable(self) -> Any:
        return self._llm


class GoogleProvider(LLMProvider):
    """Google Gemini via langchain-google-genai (placeholder)."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        # from langchain_google_genai import ChatGoogleGenerativeAI
        # self._llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
        raise NotImplementedError("GoogleProvider requires langchain-google-genai — install it and uncomment the lines above.")

    def generate(self, prompt: str) -> str: ...
    def get_runnable(self) -> Any: ...


def get_provider() -> LLMProvider:
    """Factory: read LLM_PROVIDER from config and return the correct strategy."""
    name = config.LLM_PROVIDER.lower()
    if name == "anthropic":
        return AnthropicProvider(api_key=config.ANTHROPIC_API_KEY, model=config.MODEL_NAME)
    if name == "openai":
        return OpenAIProvider(api_key=config.OPENAI_API_KEY, model=config.MODEL_NAME)
    if name == "google":
        return GoogleProvider(api_key="", model=config.MODEL_NAME)
    raise ValueError(
        f"Unknown LLM_PROVIDER='{name}'. Supported: anthropic, openai, google"
    )
