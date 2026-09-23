from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=5000)
    limit: int = Field(default=5, ge=1, le=20)


class CitationResponse(BaseModel):
    number: int
    document_id: UUID
    document_title: str
    document_version_id: UUID
    version_number: int
    page_number: int | None
    chunk_id: UUID
    excerpt: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
