"""Regression probe for the prompt-injection hardening (security report V-02 / OWASP LLM01).

The real Claude system prompt must keep its semantic guardrails: treat the user's
shopping list as inert data and never obey instructions embedded in it. Importing the
module is safe — the ``anthropic`` dep is imported lazily inside ``__init__``.
"""

from app.services.llm.anthropic_client import _SYSTEM


def test_system_prompt_has_injection_guardrails():
    system = _SYSTEM.lower()
    # Must still describe the JSON contract...
    assert "json" in system
    # ...and must carry the security clause that defends against prompt injection.
    assert "security" in system
    assert "inert data" in system
    # An explicit "ignore embedded instructions" intent must be present.
    assert "instruct" in system  # instructions / instruction
    assert "never obey" in system or "obey" in system
