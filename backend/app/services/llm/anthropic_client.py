"""Real Claude (Haiku) list parser. Used only when ``USE_MOCK_LLM=false``.

Kept intentionally small: it asks the model to return strict JSON, and falls back to
the deterministic mock parser if anything goes wrong, so a transient LLM failure never
breaks search.
"""

from __future__ import annotations

import json
import logging

from .base import LLMClient, LLMUsage, ParsedItem, ParseResult
from .mock_client import MockLLMClient

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Você normaliza listas de compras de supermercado em português do Brasil. "
    "Para cada item, retorne JSON com uma lista 'items', cada um com: "
    "'label' (texto curto para mostrar ao usuário), "
    "'search_term' (palavra-chave para buscar o produto, sem quantidade/tamanho), "
    "'quantity' (inteiro, quantas unidades a pessoa quer; padrão 1). "
    "Separe linhas compostas. Responda APENAS com JSON."
)


class AnthropicLLMClient(LLMClient):
    source_name = "claude"

    def __init__(self, api_key: str, model: str) -> None:
        import anthropic  # lazy import so the dep is optional

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._fallback = MockLLMClient()

    async def parse_list(self, raw_items: list[str]) -> ParseResult:
        prompt = "Itens:\n" + "\n".join(f"- {i}" for i in raw_items)
        try:
            msg = await self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                block.text for block in msg.content if block.type == "text"
            )
            data = json.loads(text)
            items = [
                ParsedItem(
                    raw=str(it.get("label", "")),
                    label=str(it.get("label", "")),
                    search_term=str(it.get("search_term") or it.get("label", "")),
                    quantity=int(it.get("quantity", 1) or 1),
                )
                for it in data.get("items", [])
                if it.get("search_term") or it.get("label")
            ]
            if items:
                u = msg.usage
                usage = LLMUsage(
                    input_tokens=getattr(u, "input_tokens", 0) or 0,
                    output_tokens=getattr(u, "output_tokens", 0) or 0,
                    cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
                    cache_creation_tokens=(
                        getattr(u, "cache_creation_input_tokens", 0) or 0
                    ),
                )
                return ParseResult(items=items, usage=usage)
        except Exception:  # pragma: no cover - network/parse resilience
            logger.exception("Claude parse_list failed; falling back to mock parser")
        # Fallback: mock parser (usage=None → caller estimates cost).
        return await self._fallback.parse_list(raw_items)
