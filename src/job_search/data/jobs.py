from __future__ import annotations

import json
import math
import time

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


def build_jobs_dataset(
    *,
    results_wanted: int | None = None,
    sleep_between: float | None = None,
    max_queries: int | None = None,
) -> int:
    """Scrape jobs for dataset1's queries, appending to jobs.jsonl as results land.

    Incremental + crash-safe (each job flushed immediately) and resumable (jobs already
    in the file are skipped by url), since LinkedIn scraping is slow and rate-limited.
    Returns the number of new jobs written this run.
    """
    results_wanted = results_wanted if results_wanted is not None else settings.jobs_per_query
    sleep_between = sleep_between if sleep_between is not None else settings.jobs_sleep_between
    max_queries = max_queries if max_queries is not None else settings.max_job_queries

    tasks = [
        (entry["id"], JobQuery.model_validate(raw))
        for entry in read_jsonl(settings.dataset1_path)
        for raw in entry["queries"]
    ]
    if max_queries is not None:
        tasks = tasks[:max_queries]

    seen_urls: set[str] = set()
    if settings.jobs_path.exists():
        seen_urls = {rec["job"]["job_url"] for rec in read_jsonl(settings.jobs_path)}

    settings.jobs_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with settings.jobs_path.open("a", encoding="utf-8") as f, tqdm(
        total=len(tasks), desc="Scraping LinkedIn", unit="query"
    ) as pbar:
        for resume_id, query in tasks:
            for listing in fetch_jobs_for_query(query, results_wanted):
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
            pbar.set_postfix(jobs=written)
            if sleep_between:
                time.sleep(sleep_between)

    return written
