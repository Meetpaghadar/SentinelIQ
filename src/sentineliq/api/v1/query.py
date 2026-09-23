from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sentineliq.api.v1.schemas import (
    CitationResponse,
    QueryRequest,
    QueryResponse,
)
from sentineliq.auth.dependencies import (
    AuthenticatedUser,
)
from sentineliq.auth.permissions import require_permission
from sentineliq.db.session import get_db
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.rag.service import RAGService
from sentineliq.retrieval.service import RetrievalService

router = APIRouter(prefix="/api/v1", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query_knowledge(
    request: QueryRequest,
    current_user: AuthenticatedUser = Depends(require_permission("knowledge:query")),
    session: Session = Depends(get_db),
) -> QueryResponse:
    embedding_service = EmbeddingService()
    retrieval_service = RetrievalService(embedding_service)
    rag_service = RAGService(retrieval_service)

    result = rag_service.answer(
        session=session,
        tenant_id=current_user.tenant_id,
        question=request.question,
        limit=request.limit,
    )

    return QueryResponse(
        answer=result.answer,
        citations=[
            CitationResponse(
                number=citation.number,
                document_id=citation.document_id,
                document_title=citation.document_title,
                document_version_id=citation.document_version_id,
                version_number=citation.version_number,
                page_number=citation.page_number,
                chunk_id=citation.chunk_id,
                excerpt=citation.excerpt,
            )
            for citation in result.citations
        ],
    )
