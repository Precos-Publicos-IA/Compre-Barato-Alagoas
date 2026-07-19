"""LLM client for SEFAZ output validation (cheap model) and training (capable model).

Uses Claude Haiku for real-time validation (cheap, fast) and Claude Sonnet for
the daily training job (more capable, slower, costlier).

When no API key is available, falls back to deterministic rule-based validation.
"""

from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

# Validation system prompt (used with cheap model)
_VALIDATION_SYSTEM = """\
You validate SEFAZ NFC-e search results for a Brazilian grocery price app. \
For each product, check if the SEFAZ descriptions actually match what the user wants. \
SEFAZ data is messy: businesses name products differently. \
Focus on category mismatches (dog food vs human food, cleaning vs cooking). \
Abbreviated or ugly names are normal, not invalid. \
Respond with JSON ONLY.\
"""

# Training system prompt (used with capable model)
_TRAINING_SYSTEM = """\
You are the training engine for a Brazilian grocery price comparison app (Alagoas). \
You analyze failed searches and SEFAZ data patterns to improve the product catalog. \
Each product has search_queries (sent to SEFAZ API), sefaz_terms_positive (correct matches), \
sefaz_terms_negative (false positives), brands, and sizes. \
Your job: suggest improvements based on training flags. Be conservative — \
better to miss a variant than add a false positive. \
Respond with JSON ONLY.\
"""


class ValidationLLMClient:
    """Handles LLM calls for validation and training."""

    def __init__(self, api_key: str = "", cheap_model: str = "claude-haiku-4-5-20251001",
                 capable_model: str = "claude-sonnet-5", timeout: float = 30.0):
        self._api_key = api_key
        self._cheap_model = cheap_model
        self._capable_model = capable_model
        self._timeout = timeout
        self._client = None
        if api_key:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)
            except ImportError:
                logger.warning("anthropic package not installed; validation LLM disabled")

    async def validate_sefaz_output(self, prompt: str) -> str | None:
        """Call the cheap model to validate SEFAZ output.

        Returns the raw response text, or None if unavailable.
        """
        if not self._client:
            return None
        try:
            msg = await self._client.messages.create(
                model=self._cheap_model,
                max_tokens=2048,
                system=_VALIDATION_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(
                block.text for block in msg.content if block.type == "text"
            )
        except Exception:
            logger.exception("Validation LLM call failed")
            return None

    async def training_analysis(self, prompt: str) -> str | None:
        """Call the capable model for training analysis.

        Returns the raw response text, or None if unavailable.
        """
        if not self._client:
            return None
        try:
            msg = await self._client.messages.create(
                model=self._capable_model,
                max_tokens=4096,
                system=_TRAINING_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(
                block.text for block in msg.content if block.type == "text"
            )
        except Exception:
            logger.exception("Training LLM call failed")
            return None

    async def training_analysis_batch(
        self,
        items: list[tuple[str, str]],
        *,
        poll_interval: float = 30.0,
        max_wait: float = 24 * 60 * 60,
    ) -> dict[str, str] | None:
        """Analyse many training batches in ONE Message Batches API submission.

        ``items`` is a list of ``(custom_id, prompt)``. Returns a mapping of
        ``custom_id -> raw response text`` for the batches that succeeded, or
        ``None`` if the LLM is unavailable.

        The Batches API is asynchronous (results land over minutes-to-24h), which
        is exactly why it belongs in the once-a-day training job and not in the
        real-time validation path. We submit once, then poll until the batch ends.
        """
        if not self._client or not items:
            return None
        try:
            batch = await self._client.messages.batches.create(
                requests=[
                    {
                        "custom_id": cid,
                        "params": {
                            "model": self._capable_model,
                            "max_tokens": 4096,
                            "system": _TRAINING_SYSTEM,
                            "messages": [{"role": "user", "content": prompt}],
                        },
                    }
                    for cid, prompt in items
                ]
            )
        except Exception:
            logger.exception("Failed to submit training batch")
            return None

        # Poll until the batch finishes processing.
        waited = 0.0
        while waited < max_wait:
            try:
                status = await self._client.messages.batches.retrieve(batch.id)
            except Exception:
                logger.exception("Failed to poll training batch %s", batch.id)
                return None
            if status.processing_status == "ended":
                break
            await asyncio.sleep(poll_interval)
            waited += poll_interval
        else:
            logger.warning("Training batch %s did not finish within max_wait", batch.id)
            return None

        # Collect results, keyed by custom_id.
        out: dict[str, str] = {}
        try:
            async for entry in await self._client.messages.batches.results(batch.id):
                if entry.result.type != "succeeded":
                    logger.warning("Training batch item %s: %s", entry.custom_id, entry.result.type)
                    continue
                text = "".join(
                    block.text for block in entry.result.message.content
                    if block.type == "text"
                )
                out[entry.custom_id] = text
        except Exception:
            logger.exception("Failed to read training batch results %s", batch.id)
            return None
        return out

    @property
    def available(self) -> bool:
        return self._client is not None


def build_validation_llm(settings) -> "ValidationLLMClient | None":
    """Construct the catalog validation/training client from settings.

    Returns ``None`` when the app is in mock mode or has no API key, so the
    catalog pipeline transparently falls back to deterministic rules.
    """
    if getattr(settings, "use_mock_llm", True) or not getattr(settings, "anthropic_api_key", ""):
        return None
    return ValidationLLMClient(
        api_key=settings.anthropic_api_key,
        cheap_model=settings.validation_llm_model,
        capable_model=settings.training_llm_model,
        timeout=getattr(settings, "llm_timeout_seconds", 30.0),
    )
