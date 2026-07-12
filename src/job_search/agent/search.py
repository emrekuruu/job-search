from __future__ import annotations

import time
from pathlib import Path

from job_search.agent.config import ProfileConfig
from job_search.data.jobs import fetch_jobs_for_query
from job_search.io_utils import read_jsonl
from job_search.schemas import JobListing, JobQuery

# LinkedIn rate-limits hard, and from a datacenter IP harder still.
INTER_SCRAPE_SLEEP = 2.0


def load_seen_urls(evaluations_path: Path) -> set[str]:
    """Every job_url this profile has ever evaluated.

    `job_url` is the de-facto primary key throughout the codebase, and
    `evaluations.jsonl` is the complete record of what has been scored — so it doubles as
    the "have I seen this before?" index. No separate index file to keep in sync.
    """
    if not evaluations_path.exists():
        return set()
    return {rec["job"]["job_url"] for rec in read_jsonl(evaluations_path)}


def collect_unseen(
    queries: list[JobQuery],
    cfg: ProfileConfig,
    seen_urls: set[str],
) -> tuple[list[JobListing], int]:
    """Scrape until `cfg.target_new_jobs` jobs that have never been evaluated are found.

    Each round pages deeper (`offset += results_per_query`). The paging is the whole
    point: without it, day 2 re-scrapes page 1, finds every result already evaluated, and
    has nothing left to do. With it, the agent keeps digging until it has a full batch of
    genuinely new postings.

    Returns (unseen jobs, total listings scraped). The scrape total is what distinguishes
    "LinkedIn gave us nothing" (broken) from "everything LinkedIn gave us is already
    evaluated" (a legitimately quiet day) — the caller needs both to decide whether to fail.
    """
    seen = set(seen_urls)
    new: list[JobListing] = []
    scraped = 0

    for round_i in range(cfg.max_scrape_rounds):
        offset = round_i * cfg.results_per_query
        for query in queries:
            listings = fetch_jobs_for_query(
                query,
                cfg.results_per_query,
                offset=offset,
                hours_old=cfg.hours_old,
            )
            scraped += len(listings)
            for job in listings:
                if job.job_url in seen:
                    continue
                seen.add(job.job_url)
                new.append(job)

            print(
                f"  round {round_i + 1}/{cfg.max_scrape_rounds} "
                f"offset={offset:<3} {query.search_term!r} "
                f"-> {len(listings)} scraped, {len(new)}/{cfg.target_new_jobs} unseen"
            )

            if len(new) >= cfg.target_new_jobs:
                return new[: cfg.target_new_jobs], scraped
            time.sleep(INTER_SCRAPE_SLEEP)

    return new, scraped
