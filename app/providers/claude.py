from __future__ import annotations

import os

import anthropic

from ..models import Answer, ChangeImpact, ProviderInfo, RequirementsExtraction, Summary
from .base import (
    COMPARE_SYSTEM,
    QA_SYSTEM,
    REQUIREMENTS_SYSTEM,
    SUMMARY_SYSTEM,
    truncate,
)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8000


class ClaudeProvider:
    name = "claude"

    def __init__(self, api_key_override: str | None = None) -> None:
        self._api_key_override = api_key_override
        self._client: anthropic.Anthropic | None = None

    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            model=MODEL,
            configured=bool(os.environ.get("ANTHROPIC_API_KEY")),
        )

    def _ensure_client(self) -> anthropic.Anthropic:
        key = self._api_key_override or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "No Anthropic API key available. Either set ANTHROPIC_API_KEY on "
                "the server, or provide one via the X-Anthropic-Key header."
            )
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=key)
        return self._client

    def _doc_block(self, text: str) -> dict:
        # Cached so repeated calls against the same document (summary +
        # requirements + multiple Q&A turns) read from cache instead of
        # re-paying for the prefix.
        return {
            "type": "text",
            "text": f"<document>\n{truncate(text)}\n</document>",
            "cache_control": {"type": "ephemeral"},
        }

    def _parse(self, system: str, blocks: list[dict], schema):
        client = self._ensure_client()
        message = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": blocks}],
            output_format=schema,
        )
        if message.parsed_output is None:
            raise RuntimeError(f"Model did not return a valid {schema.__name__}")
        return message.parsed_output

    def summarize(self, document_text: str) -> Summary:
        return self._parse(
            SUMMARY_SYSTEM,
            [
                self._doc_block(document_text),
                {"type": "text", "text": "Produce the structured summary of this document."},
            ],
            Summary,
        )

    def extract_requirements(self, document_text: str) -> RequirementsExtraction:
        return self._parse(
            REQUIREMENTS_SYSTEM,
            [
                self._doc_block(document_text),
                {"type": "text", "text": "Extract all requirements from this document."},
            ],
            RequirementsExtraction,
        )

    def answer_question(self, document_text: str, question: str) -> Answer:
        return self._parse(
            QA_SYSTEM,
            [
                self._doc_block(document_text),
                {
                    "type": "text",
                    "text": f"Question: {question}\n\nAnswer using only the document above.",
                },
            ],
            Answer,
        )

    def compare_documents(self, before_text: str, after_text: str) -> ChangeImpact:
        return self._parse(
            COMPARE_SYSTEM,
            [
                {"type": "text", "text": f"<before>\n{truncate(before_text)}\n</before>"},
                {"type": "text", "text": f"<after>\n{truncate(after_text)}\n</after>"},
                {
                    "type": "text",
                    "text": "Produce the structured change-impact report.",
                },
            ],
            ChangeImpact,
        )
