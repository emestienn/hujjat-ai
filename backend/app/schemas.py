"""Pydantic models used by the REST API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: str
    filename: str
    pages: int
    chunks: int
    size_bytes: int
    created_at: datetime


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[str] | None = Field(
        default=None, description="Limit the search to these documents. Empty = all documents."
    )
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class Source(BaseModel):
    index: int = Field(description="Citation number used in the answer, e.g. [1]")
    document_id: str
    filename: str
    page: int
    text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    provider: str


class HealthOut(BaseModel):
    status: str
    provider: str
    semantic_search: bool
    documents: int
