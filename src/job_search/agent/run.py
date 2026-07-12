from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from job_search import store
from job_search.agent import report, search
from job_search.agent.config import ProfileConfig
from job_search.agent.evaluate import evaluate_fit_strict
from job_search.agents import generate_queries
from job_search.concurrency import map_to_jsonl
from job_search.config import settings
from job_search.preferences import build_input, none_if_any
from job_search.providers import get_model
from job_search.schemas import JobListing
from job_search.spaces.search.ocr import extract_resume_text
from job_search.store import ProfileStore


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


async def run_profile(bucket: str, profile: str, target_new_jobs: int | None) -> dict[str, Any]:
    """One daily pass for one profile. Returns the run log."""
    started_at = _utc_now()
    ps = ProfileStore(bucket, profile)

    with tempfile.TemporaryDirectory(prefix=f"job-agent-{profile}-") as tmp:
        workdir = Path(tmp)

        # --- pull: resume + config are required; evaluations/status may not exist yet ---
        resume_path = workdir / store.RESUME
        ps.download(store.RESUME, resume_path)
        cfg = ProfileConfig.model_validate(ps.read_json(store.CONFIG, workdir))
        if target_new_jobs is not None:
            cfg = cfg.model_copy(update={"target_new_jobs": target_new_jobs})

        evaluations_path = workdir / store.EVALUATIONS
        ps.download_optional(store.EVALUATIONS, evaluations_path)
        status = ps.read_json_optional(store.STATUS, workdir)

        seen_urls = search.load_seen_urls(evaluations_path)
        print(f"[{profile}] {len(seen_urls)} jobs already evaluated; want {cfg.target_new_jobs} new")

        resume_text = extract_resume_text(resume_path)
        full_input = build_input(
            resume_text,
            cfg.extra,
            none_if_any(cfg.job_type),
            none_if_any(cfg.modality),
            none_if_any(cfg.location),
        )

        # --- queries (teacher) ---
        model = get_model("deepseek")
        queryset, _ = await generate_queries(full_input, cfg.category, model=model)
        queries = queryset.queries[: cfg.n_queries]
        print(f"[{profile}] queries: {[q.search_term for q in queries]}")

        # --- scrape until we have target_new_jobs postings worth evaluating ---
        h = search.collect_unseen(queries, cfg, seen_urls)

        if h.rejected:
            print(f"[{profile}] screened out {h.rejected_total} before evaluating:")
            for reason, n in h.rejected.most_common():
                print(f"    {n:>4}x  {reason}")

        # A run that scrapes nothing at all is broken, not quiet — almost always LinkedIn
        # throttling this IP. Fail loudly so the Job goes red instead of silently writing
        # an empty day.
        if h.scraped == 0:
            raise RuntimeError(
                f"[{profile}] LinkedIn returned 0 listings across "
                f"{cfg.max_scrape_rounds} rounds x {len(queries)} queries. "
                "Almost certainly rate-limited / blocked; consider proxies."
            )

        new_jobs = h.jobs
        if not new_jobs:
            print(
                f"[{profile}] scraped {h.scraped}, but nothing survived to evaluate "
                f"({h.already_evaluated} already done, {h.rejected_total} screened out) "
                "— nothing new today."
            )
            return _log(profile, started_at, cfg, queries, h, 0)

        # --- evaluate (teacher, concurrent) ---
        # map_to_jsonl appends+flushes each record as it lands (crash-safe) and rebuilds
        # its own skip-set from the file, so it re-checks "already evaluated" independently
        # of collect_unseen. Per-item failures are logged and skipped — correct for a
        # nightly batch — but a 100% failure rate is a broken run, caught below.
        async def work(job: JobListing) -> dict[str, Any]:
            evaluation, reasoning = await evaluate_fit_strict(full_input, job, model=model)
            return {
                "saved_at": _utc_now(),
                "job": job.model_dump(),
                "evaluation": evaluation.model_dump(),
                "reasoning": reasoning,
            }

        written = await map_to_jsonl(
            new_jobs,
            work=work,
            out_path=evaluations_path,
            item_key=lambda j: j.job_url,
            record_key=lambda r: r["job"]["job_url"],
            concurrency=settings.teacher_concurrency,
            desc=f"Evaluating ({profile})",
            request_pacing=settings.teacher_request_pacing,
        )
        if written == 0:
            raise RuntimeError(
                f"[{profile}] found {len(new_jobs)} new jobs but every evaluation failed. "
                "Check the [skip] lines above (DeepSeek key? rate limit? schema drift?)."
            )

        # --- report + push (agent owns evaluations.jsonl / .xlsx / runs; never status.json) ---
        report_path = workdir / store.REPORT
        rows = report.build_xlsx(evaluations_path, status, report_path)

        log = _log(profile, started_at, cfg, queries, h, written)
        ps.upload([
            (evaluations_path, store.EVALUATIONS),
            (report_path, store.REPORT),
            (json.dumps(log, ensure_ascii=False, indent=2).encode("utf-8"),
             f"runs/{started_at}.json"),
        ])
        print(f"[{profile}] +{written} evaluations, {rows} rows in {store.REPORT}")
        return log


def _log(
    profile: str,
    started_at: str,
    cfg: ProfileConfig,
    queries: list[Any],
    h: search.Harvest,
    evaluated: int,
) -> dict[str, Any]:
    return {
        "profile": profile,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "category": cfg.category,
        "queries": [q.model_dump() for q in queries],
        "scraped": h.scraped,
        "already_evaluated": h.already_evaluated,
        # Kept per-reason: a screen quietly eating every result should look like a screen
        # problem in the log, not like "LinkedIn had a slow day".
        "screened_out": h.rejected_total,
        "screened_out_by_reason": dict(h.rejected.most_common()),
        "to_evaluate": len(h.jobs),
        "evaluated": evaluated,
        "target_new_jobs": cfg.target_new_jobs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Daily headless job search for one profile, backed by a HF Storage Bucket."
    )
    parser.add_argument("--bucket", required=True, help="e.g. emrekuruu/job-agent")
    parser.add_argument("--profile", required=True, help="e.g. gf-data-analyst")
    parser.add_argument(
        "--target-new-jobs",
        type=int,
        default=None,
        help="Override config.json's target_new_jobs (handy for a small smoke run).",
    )
    args = parser.parse_args()
    asyncio.run(run_profile(args.bucket, args.profile, args.target_new_jobs))


if __name__ == "__main__":
    main()
