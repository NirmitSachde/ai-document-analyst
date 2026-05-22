from __future__ import annotations

import os

from .base import LLMProvider


def get_provider(api_key_override: str | None = None) -> LLMProvider:
    """Return the configured LLM provider.

    Selected via the LLM_PROVIDER env var:
      - "claude" (default) -> Anthropic Claude (claude-sonnet-4-6)
      - "gemini"           -> Google Gemini (gemini-2.5-flash)

    If `api_key_override` is set, the provider will use that key instead of the
    server's env-var key. Used to support the BYO key UI: the frontend can pass
    `X-Gemini-Key` (or `X-Anthropic-Key`) per-request so visitors can spend
    their own quota.
    """
    name = os.environ.get("LLM_PROVIDER", "claude").strip().lower()
    if name == "claude":
        from .claude import ClaudeProvider
        return ClaudeProvider(api_key_override=api_key_override)
    if name == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(api_key_override=api_key_override)
    raise RuntimeError(
        f"Unknown LLM_PROVIDER {name!r}. Set LLM_PROVIDER to 'claude' or 'gemini'."
    )


__all__ = ["LLMProvider", "get_provider"]
