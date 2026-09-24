from dataclasses import dataclass

from sentineliq.retrieval.models import (
    RetrievalResult,
)


@dataclass(frozen=True, slots=True)
class ContextItem:
    number: int
    result: RetrievalResult
    rendered: str


@dataclass(frozen=True, slots=True)
class AssembledContext:
    text: str
    items: tuple[ContextItem, ...]


class ContextAssembler:
    def assemble(
        self,
        results: list[RetrievalResult],
    ) -> AssembledContext:
        items: list[ContextItem] = []
        rendered_sections: list[str] = []

        for number, result in enumerate(
            results,
            start=1,
        ):
            rendered = "\n".join(
                [
                    f"[{number}]",
                    f"Document: {result.document_title}",
                    f"Version: {result.version_number}",
                    f"Page: {result.page_number}",
                    (f"Retrieval: {result.retrieval_method}"),
                    "Evidence:",
                    result.content,
                ]
            )

            items.append(
                ContextItem(
                    number=number,
                    result=result,
                    rendered=rendered,
                )
            )

            rendered_sections.append(rendered)

        return AssembledContext(
            text="\n\n".join(rendered_sections),
            items=tuple(items),
        )
