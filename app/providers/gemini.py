from __future__ import annotations

import copy
import os
from typing import Any, Type, TypeVar

import google.generativeai as genai
from google.generativeai.types import content_types
from pydantic import BaseModel

from ..models import Answer, ChangeImpact, ProviderInfo, RequirementsExtraction, Summary
from .base import (
    COMPARE_SYSTEM,
    QA_SYSTEM,
    REQUIREMENTS_SYSTEM,
    SUMMARY_SYSTEM,
    truncate,
)

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
MAX_OUTPUT_TOKENS = 8000

T = TypeVar("T", bound=BaseModel)


# Keys present in the SDK-built schema that the older google-generativeai
# Schema proto can't represent. The big offender is `default` (Pydantic emits
# it for any field with a default value or default_factory, and the proto
# blows up with "Unknown field for Schema: default" when it sees one).
_UNSUPPORTED_SCHEMA_KEYS = {"default"}


def _strip_unsupported(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _strip_unsupported(v) for k, v in node.items() if k not in _UNSUPPORTED_SCHEMA_KEYS}
    if isinstance(node, list):
        return [_strip_unsupported(item) for item in node]
    return node


def to_gemini_schema(model: Type[BaseModel]) -> dict:
    """Convert a Pydantic model into a schema dict the SDK's `_rename_schema_fields`
    will happily turn into a `protos.Schema`.

    We let the SDK's own `_schema_for_class` do the heavy lifting (proto-style
    uppercased types, ref resolution, etc.), then strip the `default` keys it
    leaves in — those are what trip up the proto constructor.
    """
    raw = content_types._schema_for_class(model)
    return _strip_unsupported(copy.deepcopy(raw))


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key_override: str | None = None) -> None:
        # Per-request override: the frontend can send X-Gemini-Key to use a
        # visitor's own key instead of the server's env var. Override is NOT
        # persisted on the provider instance — providers are constructed per
        # request by main.py.
        self._api_key_override = api_key_override

    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            model=MODEL,
            configured=bool(os.environ.get("GEMINI_API_KEY")),
        )

    def _resolve_key(self) -> str:
        if self._api_key_override:
            return self._api_key_override
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(
                "No Gemini API key available. Either set GEMINI_API_KEY on the "
                "server, or provide one via the X-Gemini-Key header (the BYO "
                "key path in the Settings panel)."
            )
        return key

    def _generate(self, system: str, parts: list[str], schema: Type[T]) -> T:
        # Configure on every call rather than caching a singleton; the SDK is
        # module-global, so caching would race with concurrent BYO-key requests.
        genai.configure(api_key=self._resolve_key())
        model = genai.GenerativeModel(
            model_name=MODEL,
            system_instruction=system,
            generation_config={
                "response_mime_type": "application/json",
                # `response_schema` accepts a dict that we hand-shape to dodge
                # the SDK's class-path schema generation, which trips over
                # Pydantic's `default` keys (e.g. on optional list/notes fields).
                "response_schema": to_gemini_schema(schema),
                "max_output_tokens": MAX_OUTPUT_TOKENS,
            },
        )
        response = model.generate_content(parts)
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError(f"{self.name} returned an empty response for {schema.__name__}")
        return schema.model_validate_json(text)

    def summarize(self, document_text: str) -> Summary:
        return self._generate(
            SUMMARY_SYSTEM,
            [
                f"<document>\n{truncate(document_text)}\n</document>",
                "Produce the structured summary of this document.",
            ],
            Summary,
        )

    def extract_requirements(self, document_text: str) -> RequirementsExtraction:
        return self._generate(
            REQUIREMENTS_SYSTEM,
            [
                f"<document>\n{truncate(document_text)}\n</document>",
                "Extract all requirements from this document.",
            ],
            RequirementsExtraction,
        )

    def answer_question(self, document_text: str, question: str) -> Answer:
        return self._generate(
            QA_SYSTEM,
            [
                f"<document>\n{truncate(document_text)}\n</document>",
                f"Question: {question}\n\nAnswer using only the document above.",
            ],
            Answer,
        )

    def compare_documents(self, before_text: str, after_text: str) -> ChangeImpact:
        return self._generate(
            COMPARE_SYSTEM,
            [
                f"<before>\n{truncate(before_text)}\n</before>",
                f"<after>\n{truncate(after_text)}\n</after>",
                "Produce the structured change-impact report.",
            ],
            ChangeImpact,
        )
