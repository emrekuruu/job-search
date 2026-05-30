from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from job_search.config import settings

if TYPE_CHECKING:
    from pydantic_ai import Agent
    from pydantic_ai.agent import AgentRunResult
    from pydantic_ai.models import Model
    from pydantic_ai.settings import ModelSettings

BACKENDS = ("deepseek", "vllm")

# Transient HTTP statuses worth retrying (rate limits + overload + gateway errors).
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


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


def teacher_model_settings() -> "ModelSettings":
    """Per-call generation settings for the teacher."""
    from pydantic_ai.settings import ModelSettings

    return ModelSettings(
        temperature=settings.teacher_temperature,
        max_tokens=settings.teacher_max_tokens,
        timeout=settings.teacher_timeout,
    )


def _is_retryable(exc: Exception) -> bool:
    import openai
    from pydantic_ai.exceptions import ModelHTTPError

    if isinstance(exc, ModelHTTPError):
        return exc.status_code in RETRYABLE_STATUS
    return isinstance(
        exc,
        (
            openai.APITimeoutError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.InternalServerError,
        ),
    )


async def run_with_retry(
    agent: "Agent",
    user_prompt: str,
    *,
    model: "Model",
    model_settings: "ModelSettings",
) -> "AgentRunResult":
    """Run an agent async with exponential backoff on rate-limit/transient errors.

    Non-transient errors (e.g. output validation) propagate immediately. After the
    retry budget is exhausted the last error is raised rather than silently skipped.
    """
    attempt = 0
    while True:
        try:
            return await agent.run(user_prompt, model=model, model_settings=model_settings)
        except Exception as exc:  # noqa: BLE001 - re-raised unless transient
            attempt += 1
            if attempt > settings.teacher_max_retries or not _is_retryable(exc):
                raise
            delay = settings.teacher_retry_base_delay * 2 ** (attempt - 1)
            delay += random.uniform(0, delay * 0.1)  # jitter
            await asyncio.sleep(delay)
