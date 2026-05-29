from __future__ import annotations

import math
import time

from job_search.config import settings
from job_search.io_utils import read_jsonl, write_jsonl
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
    sleep_between: float = 3.0,
) -> int:
    """Read dataset1 queries, scrape jobs, dedupe per resume by url, write jobs.jsonl."""
    results_wanted = results_wanted if results_wanted is not None else settings.jobs_per_query

    records: list[dict] = []
    for entry in read_jsonl(settings.dataset1_path):
        resume_id = entry["id"]
        seen_urls: set[str] = set()
        for raw_query in entry["queries"]:
            query = JobQuery.model_validate(raw_query)
            listings = fetch_jobs_for_query(query, results_wanted)
            for listing in listings:
                if listing.job_url in seen_urls:
                    continue
                seen_urls.add(listing.job_url)
                records.append(
                    {
                        "resume_id": resume_id,
                        "query": query.model_dump(),
                        "job": listing.model_dump(),
                    }
                )
            if sleep_between:
                time.sleep(sleep_between)

    return write_jsonl(settings.jobs_path, records)
