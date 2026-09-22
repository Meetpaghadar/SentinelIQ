from sqlalchemy import select

from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.models import Chunk


def main() -> None:
    embedding_service = EmbeddingService()

    with SessionLocal() as session:
        chunks = list(
            session.scalars(select(Chunk).where(Chunk.embedding.is_(None)).order_by(Chunk.id))
        )

        if not chunks:
            print("No chunks need embeddings.")
            return

        print(f"Embedding {len(chunks)} chunks...")

        embeddings = embedding_service.embed_texts([chunk.content for chunk in chunks])

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding

        session.commit()

        print(f"Embedded {len(chunks)} chunks.")


if __name__ == "__main__":
    main()
