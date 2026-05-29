from __future__ import annotations

from typing import TYPE_CHECKING

from job_search.config import settings

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult
    from pydantic_ai.models import Model

BACKENDS = ("deepseek", "vllm")


def _require(value: str | None, name: str) -> str:
    if not value:
        raise ValueError(f"{name} is not set; required for this backend.")
    return value


def get_model(backend: str) -> "Model":
    """Return a PydanticAI model for the given backend.

    - deepseek: the reasoning teacher (emits reasoning_content -> ThinkingPart)
    - vllm:     the distilled student, served OpenAI-compatible
    """
    if backend == "deepseek":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.deepseek import DeepSeekProvider

        provider = DeepSeekProvider(api_key=_require(settings.deepseek_api_key, "DEEPSEEK_API_KEY"))
        return OpenAIChatModel(settings.teacher_model, provider=provider)

    if backend == "vllm":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        provider = OpenAIProvider(
            base_url=_require(settings.vllm_api_base, "VLLM_API_BASE"),
            api_key=settings.vllm_api_key,
        )
        return OpenAIChatModel(settings.student_model, provider=provider)

    raise ValueError(f"unknown backend {backend!r}; expected one of {BACKENDS}")


def extract_reasoning(result: "AgentRunResult") -> str:
    """Concatenate the reasoning trace (ThinkingParts) from a run's response messages."""
    from pydantic_ai.messages import ModelResponse, ThinkingPart

    chunks: list[str] = []
    for message in result.all_messages():
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ThinkingPart) and part.content:
                    chunks.append(part.content)
    return "\n".join(chunks).strip()
