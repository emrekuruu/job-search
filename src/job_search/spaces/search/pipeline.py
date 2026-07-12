from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from job_search.data.jobs import fetch_jobs_for_query
from job_search.preferences import build_input, none_if_any
from job_search.schemas import JobListing
from job_search.spaces.search.inference import evaluate_fit_batch, generate_queries


def stream_pipeline(
    resume_text: str,
    extra: str | None,
    *,
    job_type: str | None = None,
    modality: str | None = None,
    location: str | None = None,
    n_queries: int = 3,
    results_per_query: int = 3,
    inter_query_sleep: float = 1.0,
) -> Iterator[dict[str, Any]]:
    """Yield semantic pipeline events so the UI can stream updates.

    Event shapes:
      {"kind": "query_token", "reasoning": str}                                # streaming
      {"kind": "queries", "queries": [JobQuery, ...], "reasoning": str}        # final
      {"kind": "jobs_after_query", "query": JobQuery, "new_jobs": [JobListing], "total": int}
      {"kind": "eval_token", "job": JobListing, "reasoning": str}              # streaming
      {"kind": "evaluation", "job": JobListing, "evaluation": FitEvaluation, "reasoning": str}
      {"kind": "done", "ranked": [(JobListing, FitEvaluation, str)]}
    """
    job_type = none_if_any(job_type)
    modality = none_if_any(modality)
    location = none_if_any(location)

    full_input = build_input(resume_text, extra, job_type, modality, location)

    # 1) Query generation — streaming. The student emits <think>...reasoning...</think>
    #    {json}, so the cumulative `text` during streaming is mostly the reasoning block
    #    until `</think>` appears. We surface the reasoning portion to the UI live.
    queryset = None
    q_reasoning = ""
    for ev in generate_queries(full_input, category="general"):
        if ev["kind"] == "token":
            # Best-effort live reasoning: everything between the opening <think> tag and
            # the (possibly still-absent) closing </think>.
            cumul = ev["text"]
            partial_reasoning = _live_reasoning(cumul)
            if partial_reasoning:
                yield {"kind": "query_token", "reasoning": partial_reasoning}
        elif ev["kind"] == "done":
            queryset = ev["result"]
            q_reasoning = ev["reasoning"]

    assert queryset is not None, "query gen did not produce a 'done' event"
    queries = queryset.queries[:n_queries]
    yield {"kind": "queries", "queries": queries, "reasoning": q_reasoning}

    # 2) Job fetching — sequential + polite (LinkedIn rate-limits hard).
    seen_urls: set[str] = set()
    all_jobs: list[JobListing] = []
    for i, q in enumerate(queries):
        listings = fetch_jobs_for_query(q, results_per_query)
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
            time.sleep(inter_query_sleep)

    if not all_jobs:
        yield {"kind": "done", "ranked": []}
        return

    # 3) Fit evaluation — ONE @spaces.GPU call streams events for every job.
    # See inference._run_fit_eval_batch for why batched (proxy-token expiry).
    results: list[tuple] = []
    for ev in evaluate_fit_batch(full_input, all_jobs):
        job = ev["job"]
        if ev["kind"] == "token":
            partial_reasoning = _live_reasoning(ev["text"])
            if partial_reasoning:
                yield {"kind": "eval_token", "job": job, "reasoning": partial_reasoning}
        elif ev["kind"] == "done":
            ev_obj = ev["result"]
            e_reasoning = ev["reasoning"]
            results.append((job, ev_obj, e_reasoning))
            yield {
                "kind": "evaluation",
                "job": job,
                "evaluation": ev_obj,
                "reasoning": e_reasoning,
            }

    # 4) Final ranking.
    ranked = sorted(results, key=lambda r: r[1].total, reverse=True)
    yield {"kind": "done", "ranked": ranked}


def _live_reasoning(cumul: str) -> str:
    """Extract the in-progress reasoning text from a partial generation.

    During streaming the model emits `<think>\n<reasoning so far>` and (eventually)
    `</think>\n\n{json}`. We surface only the reasoning portion to the UI — once
    `</think>` shows up we keep showing what was inside the block (the JSON tail is
    presented as the final structured result instead).
    """
    s = cumul.lstrip()
    if not s.startswith("<think>"):
        return ""
    s = s[len("<think>") :]
    if "</think>" in s:
        s = s.split("</think>", 1)[0]
    return s.strip()
