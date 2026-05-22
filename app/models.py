from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentMeta(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    char_count: int
    uploaded_at: datetime


class UploadResponse(BaseModel):
    document: DocumentMeta
    preview: str


class Entity(BaseModel):
    name: str
    type: str = Field(description="person | organization | date | money | location | other")
    context: str = Field(description="Short snippet showing how this entity appears in the document")


class Summary(BaseModel):
    overview: str
    key_points: list[str]
    entities: list[Entity]
    action_items: list[str]
    dates: list[str]


class Requirement(BaseModel):
    id: str = Field(description="Stable ID like REQ-001, REQ-002")
    description: str
    priority: Literal["high", "medium", "low"]
    category: str = Field(description="functional | non-functional | constraint | assumption | other")
    dependencies: list[str] = Field(default_factory=list, description="IDs of other requirements this depends on")


class RequirementsExtraction(BaseModel):
    requirements: list[Requirement]
    notes: str = Field(default="", description="Anything the extractor flagged for human review")


class Citation(BaseModel):
    quote: str
    location_hint: str = Field(description="Section or rough position in the document")


class Answer(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: Literal["high", "medium", "low"]


class AskRequest(BaseModel):
    doc_id: int
    question: str


class CompareRequest(BaseModel):
    doc_id_before: int
    doc_id_after: int


class RequirementChange(BaseModel):
    kind: Literal["added", "removed", "modified"]
    requirement_id: str = Field(
        description="ID from whichever side carries it (after for added/modified, before for removed)"
    )
    before: str | None = Field(default=None, description="Requirement text in the older version, if applicable")
    after: str | None = Field(default=None, description="Requirement text in the newer version, if applicable")
    rationale: str = Field(description="Why this change matters to stakeholders")


class ChangeImpact(BaseModel):
    summary: str
    changes: list[RequirementChange]
    risk_level: Literal["high", "medium", "low"]
    stakeholder_notes: str


class QueryRecord(BaseModel):
    id: int
    document_id: int | None
    kind: str
    question: str | None
    response_json: str
    created_at: datetime


class ProviderInfo(BaseModel):
    name: str
    model: str
    configured: bool
