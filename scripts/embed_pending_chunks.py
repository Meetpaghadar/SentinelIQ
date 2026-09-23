import argparse

from sqlalchemy import func, select

from sentineliq.db.session import SessionLocal
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.models import Chunk


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed SentinelIQ chunks that do not have embeddings."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
    )

    args = parser.parse_args()

    if args.batch_size <= 0:
        raise ValueError("batch-size must be greater than zero")

    embedding_service = EmbeddingService()

    with SessionLocal() as session:
        pending_count = session.scalar(
            select(func.count()).select_from(Chunk).where(Chunk.embedding.is_(None))
        )

        print(f"Pending chunks: {pending_count}")

        if pending_count == 0:
            print("Nothing to embed.")
            return

        processed = 0

        while True:
            chunks = list(
                session.scalars(
                    select(Chunk)
                    .where(Chunk.embedding.is_(None))
                    .order_by(Chunk.id)
                    .limit(args.batch_size)
                )
            )

            if not chunks:
                break

            embeddings = embedding_service.embed_texts([chunk.content for chunk in chunks])

            for chunk, embedding in zip(
                chunks,
                embeddings,
                strict=True,
            ):
                chunk.embedding = embedding

            session.commit()

            processed += len(chunks)

            print(f"Embedded: {processed}/{pending_count}")

    print("Embedding complete.")


if __name__ == "__main__":
    main()
