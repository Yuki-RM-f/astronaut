from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


GuidedMemoryKind = Literal["regrets", "wishes"]


class GuidedMemoryCandidatesCreate(BaseModel):
    kind: GuidedMemoryKind


class GuidedMemoryCandidate(BaseModel):
    memory_card_id: str
    title: str
    summary: str
    suggested_user_message: str
    source_quote: str | None = None
    source_location: str | None = None


class GuidedMemoryCandidateResponse(BaseModel):
    kind: GuidedMemoryKind
    items: list[GuidedMemoryCandidate] = Field(default_factory=list)
    empty_reason: str | None = None
