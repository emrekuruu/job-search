from __future__ import annotations

import json
import math
import random
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from job_search.config import settings
from job_search.io_utils import read_jsonl
from job_search.schemas import JobListing, JobQuery


def _clean(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def fetch_jobs_for_query(query: JobQuery, results_wanted: int) -> list[JobListing]:
    """Scrape LinkedIn for one query. Returns parsed listings (descriptions included)."""
    from jobspy import scrape_jobs

    df = scrape_jobs(
        site_name=["linkedin"],
        search_term=query.search_term,
        location=query.location or "",
        is_remote=query.is_remote,
        job_type=query.job_type,
        results_wanted=results_wanted,
        linkedin_fetch_description=True,
    )

    listings: list[JobListing] = []
    if df is None or len(df) == 0:
        return listings
    for _, row in df.iterrows():
        description = _clean(row.get("description"))
        job_url = _clean(row.get("job_url"))
        title = _clean(row.get("title"))
        if not (description and job_url and title):
            continue
        listings.append(
            JobListing(
                title=title,
                company=_clean(row.get("company")),
                location=_clean(row.get("location")),
                description=description,
                job_url=job_url,
            )
        )
    return listings


def _query_fingerprint(query: JobQuery) -> tuple:
    return (query.search_term, query.location, query.is_remote, query.job_type)


def _sample_query(resume_id: str, queries: list[dict]) -> JobQuery:
    """Deterministic per-resume sample: same seed + resume_id => same query, regardless of order."""
    rng = random.Random(f"{settings.random_seed}:{resume_id}")
    return JobQuery.model_validate(rng.choice(queries))


def reconcile_jobs_dataset() -> tuple[int, int]:
    """Enforce one-query-per-resume in jobs.jsonl.

    For each resume_id, keep records from the single query that produced the most jobs
    (ties broken by first appearance in the file). Drops everything else and rewrites
    jobs.jsonl in place. Returns (kept, dropped).
    """
    if not settings.jobs_path.exists():
        return (0, 0)

    records = list(read_jsonl(settings.jobs_path))
    by_resume: dict[str, dict[tuple, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for rec in records:
        key = _query_fingerprint(JobQuery.model_validate(rec["query"]))
        by_resume[rec["resume_id"]][key].append(rec)

    kept: list[dict] = []
    dropped = 0
    for by_query in by_resume.values():
        # dict preserves insertion order, so max() returns the first key at the max count.
        best_key = max(by_query.keys(), key=lambda k: len(by_query[k]))
        for key, recs in by_query.items():
            if key == best_key:
                kept.extend(recs)
            else:
                dropped += len(recs)

    tmp = settings.jobs_path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for rec in kept:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(settings.jobs_path)
    return (len(kept), dropped)


def build_jobs_dataset(
    *,
    results_wanted: int | None = None,
    max_queries: int | None = None,
    concurrency: int | None = None,
) -> int:
    """Scrape one sampled query per resume in parallel, appending to jobs.jsonl as results land.

    For each resume in dataset1, exactly one query is used. If the resume already has records
    in jobs.jsonl, that locked-in query is reused; otherwise a deterministic per-resume sample
    is drawn (seeded by settings.random_seed + resume_id). Resumes already represented in
    jobs.jsonl are skipped entirely this run.

    Crash-safe (each job flushed immediately), URL-deduped across resumes, and runs
    `concurrency` LinkedIn scrapes in parallel via a thread pool. Returns the number of new
    jobs written this run.
    """
    results_wanted = results_wanted if results_wanted is not None else settings.jobs_per_query
    max_queries = max_queries if max_queries is not None else settings.max_job_queries
    concurrency = concurrency if concurrency is not None else settings.jobs_concurrency

    chosen_by_resume: dict[str, JobQuery] = {}
    seen_urls: set[str] = set()
    if settings.jobs_path.exists():
        for rec in read_jsonl(settings.jobs_path):
            rid = rec["resume_id"]
            if rid not in chosen_by_resume:
                chosen_by_resume[rid] = JobQuery.model_validate(rec["query"])
            seen_urls.add(rec["job"]["job_url"])

    pending: list[tuple[str, JobQuery]] = []
    for entry in read_jsonl(settings.dataset1_path):
        rid = entry["id"]
        if rid in chosen_by_resume:
            continue
        pending.append((rid, _sample_query(rid, entry["queries"])))

    if max_queries is not None:
        pending = pending[:max_queries]

    settings.jobs_path.parent.mkdir(parents=True, exist_ok=True)
    write_lock = threading.Lock()
    written = 0

    pool = ThreadPoolExecutor(max_workers=concurrency)
    try:
        with settings.jobs_path.open("a", encoding="utf-8") as f, tqdm(
            total=len(pending), desc="Scraping LinkedIn", unit="query"
        ) as pbar:
            futures = {
                pool.submit(fetch_jobs_for_query, query, results_wanted): (resume_id, query)
                for resume_id, query in pending
            }
            failed = 0
            for fut in as_completed(futures):
                resume_id, query = futures[fut]
                try:
                    listings = fut.result()
                except Exception as e:
                    failed += 1
                    tqdm.write(
                        f"[skip] resume={resume_id} query={query.search_term!r} "
                        f"location={query.location!r}: {type(e).__name__}: {e}"
                    )
                    pbar.update(1)
                    pbar.set_postfix(jobs=written, failed=failed)
                    continue
                with write_lock:
                    for listing in listings:
                        if listing.job_url in seen_urls:
                            continue
                        seen_urls.add(listing.job_url)
                        f.write(
                            json.dumps(
                                {
                                    "resume_id": resume_id,
                                    "query": query.model_dump(),
                                    "job": listing.model_dump(),
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                        f.flush()
                        written += 1
                pbar.update(1)
                pbar.set_postfix(jobs=written, failed=failed)
    except BaseException:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        pool.shutdown(wait=True)

    return written
