from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from job_search.agents import evaluate_fit, generate_queries
from job_search.data.jobs import fetch_jobs_for_query
from job_search.schemas import JobListing

# UI labels -> JobSpy-compatible values. "Any" is treated as no preference.
JOB_TYPE_MAP: dict[str, str] = {
    "Full-time": "fulltime",
    "Part-time": "parttime",
    "Contract": "contract",
    "Internship": "internship",
}

# Modality is a soft signal — `Remote` translates to `is_remote=True` on the JobQuery side via the
# LLM; Hybrid / On-premise stay as text so the LLM can embed them in the search term.
MODALITY_MAP: dict[str, str] = {
    "Remote": "remote",
    "Hybrid": "hybrid",
    "On-premise": "on-premise",
}


def _none_if_any(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if not v or v.lower() == "any":
        return None
    return v


def _build_input(
    resume_text: str,
    extra: str | None,
    job_type: str | None,
    modality: str | None,
    location: str | None,
) -> str:
    """Pack the resume + structured preferences into one input the agent will see."""
    job_type_norm = JOB_TYPE_MAP.get(job_type or "", job_type) if job_type else None
    modality_norm = MODALITY_MAP.get(modality or "", modality) if modality else None

    lines: list[str] = []
    if job_type_norm:
        lines.append(f"- Job type: {job_type_norm}")
    if modality_norm:
        lines.append(f"- Work modality: {modality_norm}")
    if location:
        lines.append(f"- Location: {location}")
    if extra and extra.strip():
        lines.append(f"- Free-form notes: {extra.strip()}")

    if not lines:
        return resume_text
    return f"{resume_text}\n\nExplicit preferences from candidate (use these in every query):\n" + "\n".join(lines)


async def stream_pipeline(
    resume_text: str,
    extra: str | None,
    *,
    job_type: str | None = None,
    modality: str | None = None,
    location: str | None = None,
    n_queries: int = 3,
    results_per_query: int = 3,
    eval_concurrency: int = 4,
    inter_query_sleep: float = 1.0,
) -> AsyncIterator[dict[str, Any]]:
    """Yield semantic pipeline events so the UI can stream updates.

    Event shapes:
      {"kind": "queries", "queries": [JobQuery, ...], "reasoning": str}
      {"kind": "jobs_after_query", "query": JobQuery, "new_jobs": [JobListing], "total": int}
      {"kind": "evaluation", "job": JobListing, "evaluation": FitEvaluation, "reasoning": str}
      {"kind": "done", "ranked": [(JobListing, FitEvaluation, str)]}
    """
    job_type = _none_if_any(job_type)
    modality = _none_if_any(modality)
    location = _none_if_any(location)

    full_input = _build_input(resume_text, extra, job_type, modality, location)

    # 1) Query generation (single LLM call).
    queryset, q_reasoning = await generate_queries(full_input, category="general")
    queries = queryset.queries[:n_queries]
    yield {"kind": "queries", "queries": queries, "reasoning": q_reasoning}

    # 2) Job fetching — sequential + polite (LinkedIn rate-limits hard).
    seen_urls: set[str] = set()
    all_jobs: list[JobListing] = []
    for i, q in enumerate(queries):
        listings = await asyncio.to_thread(fetch_jobs_for_query, q, results_per_query)
        new_for_q: list[JobListing] = []
        for j in listings:
            if j.job_url in seen_urls:
                continue
            seen_urls.add(j.job_url)
            new_for_q.append(j)
            all_jobs.append(j)
        yield {
            "kind": "jobs_after_query",
            "query": q,
            "new_jobs": new_for_q,
            "total": len(all_jobs),
        }
        if i < len(queries) - 1 and inter_query_sleep:
            await asyncio.sleep(inter_query_sleep)

    if not all_jobs:
        yield {"kind": "done", "ranked": []}
        return

    # 3) Fit evaluation — parallel, capped via semaphore. Stream as each completes.
    sem = asyncio.Semaphore(eval_concurrency)

    async def _evaluate_one(job: JobListing):
        async with sem:
            ev, reasoning = await evaluate_fit(full_input, job)
        return job, ev, reasoning

    tasks = [asyncio.create_task(_evaluate_one(j)) for j in all_jobs]
    results: list[tuple] = []
    for fut in asyncio.as_completed(tasks):
        job, ev, reasoning = await fut
        results.append((job, ev, reasoning))
        yield {
            "kind": "evaluation",
            "job": job,
            "evaluation": ev,
            "reasoning": reasoning,
        }

    # 4) Final ranking.
    ranked = sorted(results, key=lambda r: r[1].total, reverse=True)
    yield {"kind": "done", "ranked": ranked}
