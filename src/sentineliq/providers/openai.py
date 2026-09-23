from openai import OpenAI

from sentineliq.config import get_settings
from sentineliq.contracts import (
    GenerationRequest,
    GenerationResult,
)


class OpenAIGenerationProvider:
    def __init__(self) -> None:
        settings = get_settings()

        if settings.openai_api_key is None:
            raise RuntimeError("SENTINELIQ_OPENAI_API_KEY is required")

        self._client = OpenAI(api_key=settings.openai_api_key)

        self._model = settings.generation_model

    def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        response = self._client.responses.create(
            model=self._model,
            instructions=request.instructions,
            input=request.input_text,
        )

        return GenerationResult(
            text=response.output_text,
            provider="openai",
            model=self._model,
        )
