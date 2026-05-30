from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai import Agent

from job_search.prompts import (
    build_eval_system_prompt,
    build_eval_user,
    build_query_system_prompt,
    build_query_user,
)
from job_search.providers import (
    extract_reasoning,
    get_model,
    run_with_retry,
    teacher_model_settings,
)
from job_search.schemas import FitEvaluation, JobListing, QuerySet

if TYPE_CHECKING:
    from pydantic_ai.models import Model

# retries let the model self-correct against the Pydantic validators (e.g. total == sum);
# after the retry budget it raises rather than emitting an invalid sample.
query_agent = Agent(output_type=QuerySet, system_prompt=build_query_system_prompt(), retries=3)

eval_agent = Agent(output_type=FitEvaluation, system_prompt=build_eval_system_prompt(), retries=3)


async def generate_queries(
    resume: str, category: str, *, model: "Model | None" = None
) -> tuple[QuerySet, str]:
    """Run the query agent (teacher by default); return (queries, reasoning_trace)."""
    model = model or get_model("deepseek")
    result = await run_with_retry(
        query_agent,
        build_query_user(resume, category),
        model=model,
        model_settings=teacher_model_settings(),
    )
    return result.output, extract_reasoning(result)


async def evaluate_fit(
    resume: str, job: JobListing, *, model: "Model | None" = None
) -> tuple[FitEvaluation, str]:
    """Run the fit-evaluation agent (teacher by default); return (evaluation, reasoning_trace)."""
    model = model or get_model("deepseek")
    result = await run_with_retry(
        eval_agent,
        build_eval_user(resume, job),
        model=model,
        model_settings=teacher_model_settings(),
    )
    return result.output, extract_reasoning(result)
