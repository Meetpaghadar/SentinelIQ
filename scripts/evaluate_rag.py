import argparse
import os
import sys
from time import perf_counter
from uuid import UUID

from sentineliq.contracts import (
    GenerationRequest,
    GenerationResult,
    LLMProvider,
)
from sentineliq.db.session import SessionLocal
from sentineliq.decision import (
    JevDecisionProvider,
)
from sentineliq.embeddings.service import EmbeddingService
from sentineliq.evaluation.cases import (
    FROZEN_CASES,
    HARDER_CASES,
)
from sentineliq.evaluation.retrieval_metrics import (
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)
from sentineliq.providers import (
    OpenAIGenerationProvider,
)
from sentineliq.querying import (
    QueryAnalyzer,
    QueryPlanner,
)
from sentineliq.rag.service import (
    INSUFFICIENT_EVIDENCE_ANSWER,
    RAGService,
)
from sentineliq.retrieval.service import (
    RetrievalService,
)


class CountingLLMProvider:
    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.calls = 0

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls += 1
        return self._inner.generate(request)


def _normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


def _is_insufficient_evidence(answer: str) -> bool:
    normalized = _normalize(answer)
    expected = _normalize(INSUFFICIENT_EVIDENCE_ANSWER)

    if normalized == expected:
        return True

    markers = (
        "do not provide enough information",
        "does not provide enough information",
        "not enough information to answer",
        "insufficient information to answer",
        "insufficient evidence",
        "cannot answer based on the available sources",
        "cannot answer from the available sources",
        "sources do not contain enough information",
        "sources don't contain enough information",
        "excerpts do not contain enough information",
        "excerpts don't contain enough information",
        "evidence does not contain enough information",
    )

    return any(marker in normalized for marker in markers)


def _planner_for_mode(mode: str) -> QueryPlanner:
    jev_key = os.environ.get("SENTINELIQ_JEV_API_KEY")

    decision_provider = None

    if mode == "jev" and jev_key:
        decision_provider = JevDecisionProvider(api_key=jev_key)

    return QueryPlanner(
        enable_rewrite=mode == "rewrite",
        enable_multi_query=mode in {"multi", "fusion"},
        enable_rag_fusion=mode == "fusion",
        enable_hyde=mode == "hyde",
        decision_provider=decision_provider,
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True, type=UUID)
    parser.add_argument("--set", choices=("frozen", "harder"), default="frozen")
    parser.add_argument(
        "--mode",
        choices=("baseline", "rewrite", "multi", "fusion", "hyde", "jev", "production"),
        default="baseline",
    )
    args = parser.parse_args()

    cases = FROZEN_CASES if args.set == "frozen" else HARDER_CASES
    planner = _planner_for_mode(args.mode)
    generation_provider = CountingLLMProvider(OpenAIGenerationProvider())
    rag_service = RAGService(
        RetrievalService(EmbeddingService()),
        generation_provider=generation_provider,
        query_planner=planner,
    )
    analyzer = QueryAnalyzer()

    passed = 0
    routing_correct = 0
    recall_scores: list[float] = []
    rr_scores: list[float] = []
    ndcg_scores: list[float] = []
    rag_latencies: list[float] = []

    with SessionLocal() as session:
        for index, case in enumerate(cases, start=1):
            analysis = analyzer.analyze(case.question)
            plan = planner.plan(analysis)

            if plan.path.value == case.expected_path:
                routing_correct += 1

            started = perf_counter()
            result = rag_service.answer(
                session=session,
                tenant_id=args.tenant_id,
                question=case.question,
            )
            rag_latency = perf_counter() - started
            rag_latencies.append(rag_latency)

            cited = [citation.document_title for citation in result.citations]
            insufficient = _is_insufficient_evidence(result.answer)
            expected = set(case.expected_documents)

            if case.answerable and expected:
                retrieved = list(result.retrieved_titles)
                recall_scores.append(recall_at_k(retrieved=retrieved, relevant=expected, k=5))
                rr_scores.append(reciprocal_rank(retrieved=retrieved, relevant=expected))
                ndcg_scores.append(ndcg_at_k(retrieved=retrieved, relevant=expected, k=5))

            success = False
            failure_reason = ""

            if case.answerable:
                if insufficient:
                    failure_reason = "Answerable question returned insufficient evidence"
                elif not expected.issubset(set(cited)):
                    failure_reason = "Expected document was not cited"
                elif not result.citations:
                    failure_reason = "Answerable question returned no citations"
                else:
                    success = True
            elif not insufficient:
                failure_reason = "Unanswerable question did not return insufficient evidence"
            elif result.citations:
                failure_reason = "Insufficient-evidence answer returned citations"
            else:
                success = True

            if success:
                passed += 1

            status = "PASS" if success else "FAIL"
            print()
            print(f"[{index}] {status}")
            print(f"Question: {case.question}")
            print(f"Retrieval query: {result.retrieval_query}")
            print(f"Rewrite used: {result.rewrite_used}")
            print(f"Techniques: {', '.join(result.techniques) or 'none'}")
            print(f"Expected: {case.expected_documents or None}")
            print(f"Answerable: {case.answerable}")
            print(f"Intent: {analysis.intent.value}")
            print(f"Complexity: {analysis.complexity.value}")
            print(f"Selected path: {plan.path.value}")
            print(f"Expected path: {case.expected_path}")
            print(f"Plan rewrite: {plan.rewrite}")
            print(f"Plan multi-query: {plan.multi_query}")
            print(f"Plan rag-fusion: {plan.rag_fusion}")
            print(f"Plan hyde: {plan.hyde}")
            print(f"Reranking enabled: {plan.rerank}")
            print(f"Parent expansion enabled: {plan.parent_expansion}")
            print(f"RAG latency: {rag_latency:.4f}s")
            print(f"Insufficient evidence: {insufficient}")
            print(f"Retrieved: {list(result.retrieved_titles)}")
            print(f"Cited: {cited}")
            print(f"Answer: {result.answer}")
            if not success:
                print(f"Failure reason: {failure_reason}")

    total = len(cases)
    print()
    print("=" * 30)
    print("SentinelIQ RAG Evaluation")
    print("=" * 30)
    print(f"Case set: {args.set}")
    print(f"Mode: {args.mode}")
    print(f"Passed: {passed}/{total}")
    print(f"RAG accuracy: {passed / total * 100.0:.1f}%")
    print(f"Routing accuracy: {routing_correct}/{total}")
    print(f"Generation-provider LLM calls: {generation_provider.calls}")
    print(
        "Call counting: generation-provider includes rewrite/expand/HyDE/answer. "
        "Reranker uses a separate provider (about +1 call when rerank=True)."
    )

    if rag_latencies:
        print()
        print("Latency")
        print("=" * 30)
        print(f"Average RAG latency: {sum(rag_latencies) / len(rag_latencies):.4f}s")

    if recall_scores:
        print()
        print("Retrieval Evaluation")
        print("=" * 30)
        print(f"Recall@5: {sum(recall_scores) / len(recall_scores):.3f}")
        print(f"MRR: {sum(rr_scores) / len(rr_scores):.3f}")
        print(f"nDCG@5: {sum(ndcg_scores) / len(ndcg_scores):.3f}")


if __name__ == "__main__":
    main()
