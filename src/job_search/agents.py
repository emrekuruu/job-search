from __future__ import annotations

from pydantic_ai import Agent

from job_search.prompts import (
    QUERY_SYSTEM_PROMPT,
    build_eval_system_prompt,
    build_eval_user,
    build_query_user,
)
from job_search.providers import extract_reasoning, get_model
from job_search.schemas import FitEvaluation, JobListing, QuerySet

# retries let the model self-correct against the Pydantic validators (e.g. total == sum);
# after the retry budget it raises rather than emitting an invalid sample.
query_agent = Agent(output_type=QuerySet, system_prompt=QUERY_SYSTEM_PROMPT, retries=3)

eval_agent = Agent(output_type=FitEvaluation, system_prompt=build_eval_system_prompt(), retries=3)


# Teacher is DeepSeek; `backend="vllm"` reuses the same agent to run the distilled student.
def generate_queries(resume: str, category: str, *, backend: str = "deepseek") -> tuple[QuerySet, str]:
    """Run the query agent; return (queries, reasoning_trace)."""
    result = query_agent.run_sync(build_query_user(resume, category), model=get_model(backend))
    return result.output, extract_reasoning(result)


def evaluate_fit(resume: str, job: JobListing, *, backend: str = "deepseek") -> tuple[FitEvaluation, str]:
    """Run the fit-evaluation agent; return (evaluation, reasoning_trace)."""
    result = eval_agent.run_sync(build_eval_user(resume, job), model=get_model(backend))
    return result.output, extract_reasoning(result)
