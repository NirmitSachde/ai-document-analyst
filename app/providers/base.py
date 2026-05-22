from __future__ import annotations

from typing import Protocol

from ..models import Answer, ChangeImpact, ProviderInfo, RequirementsExtraction, Summary

# Cap document text sent to either provider. Both Sonnet 4.6 (1M context) and
# Gemini 2.0 Flash (~1M context) handle this comfortably, but trimming keeps
# cost and latency predictable for the demo path.
MAX_DOC_CHARS = 200_000


SUMMARY_SYSTEM = (
    "You are a business analyst. Read the document and produce a structured "
    "summary capturing the overview, key points, named entities (people, "
    "organizations, dates, money, locations), explicit dates mentioned, and "
    "any action items. Be precise; do not invent facts the document does not "
    "state."
)

REQUIREMENTS_SYSTEM = (
    "You are a requirements engineer. Extract every requirement implied or "
    "stated in the document. For each requirement, assign a stable ID "
    "(REQ-001, REQ-002, ...), a clear single-sentence description, a "
    "priority (high/medium/low based on language like 'must', 'should', "
    "'may'), a category (functional, non-functional, constraint, "
    "assumption, other), and IDs of any requirements it depends on. If the "
    "document is not a requirements document, return an empty list and "
    "note that in 'notes'."
)

QA_SYSTEM = (
    "You answer questions strictly from the provided document. Quote the "
    "document for each citation and indicate where in the document the "
    "quote appears (e.g. 'Page 2', 'Section: Pricing'). If the answer is "
    "not in the document, set confidence to 'low' and say so."
)

COMPARE_SYSTEM = (
    "You are a requirements change analyst. Compare two versions of the same "
    "document and produce a structured change-impact report: which "
    "requirements were added, removed, or modified between the BEFORE and "
    "AFTER versions, why each change matters to stakeholders, the overall "
    "risk level (high/medium/low), and any notes the team should review. "
    "Use IDs from the AFTER version for added/modified items and from the "
    "BEFORE version for removed items. Ignore purely cosmetic edits."
)


def truncate(text: str) -> str:
    if len(text) <= MAX_DOC_CHARS:
        return text
    head = text[: MAX_DOC_CHARS - 500]
    return head + "\n\n[... document truncated for length ...]"


class LLMProvider(Protocol):
    """Common interface every LLM backend implements."""

    def info(self) -> ProviderInfo: ...

    def summarize(self, document_text: str) -> Summary: ...

    def extract_requirements(self, document_text: str) -> RequirementsExtraction: ...

    def answer_question(self, document_text: str, question: str) -> Answer: ...

    def compare_documents(self, before_text: str, after_text: str) -> ChangeImpact: ...
