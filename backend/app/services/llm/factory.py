"""Pick the LLM client implementation based on settings."""

from __future__ import annotations

import logging

from ...config import Settings
from .base import LLMClient

logger = logging.getLogger(__name__)


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.use_mock_llm or not settings.anthropic_api_key:
        from .mock_client import MockLLMClient

        if not settings.use_mock_llm and not settings.anthropic_api_key:
            logger.warning("USE_MOCK_LLM is false but no API key set; using mock LLM")
        return MockLLMClient()

    from .anthropic_client import AnthropicLLMClient

    return AnthropicLLMClient(
        api_key=settings.anthropic_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
