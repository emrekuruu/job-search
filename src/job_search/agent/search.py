from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from job_search.agent.config import ProfileConfig
from job_search.agent.filters import Screen
from job_search.data.jobs import fetch_jobs_for_query
from job_search.io_utils import read_jsonl
from job_search.schemas import JobListing, JobQuery

# LinkedIn rate-limits hard, and from a datacenter IP harder still.
INTER_SCRAPE_SLEEP = 2.0


@dataclass
class Harvest:
    jobs: list[JobListing] = field(default_factory=list)
    scraped: int = 0
    already_evaluated: int = 0
    #: reject reason -> count. Surfaced in the run log so a screen that is quietly eating
    #: everything is visible rather than looking like "LinkedIn had nothing today".
    rejected: Counter[str] = field(default_factory=Counter)

    @property
    def rejected_total(self) -> int:
        return sum(self.rejected.values())


def load_seen_urls(evaluations_path: Path) -> set[str]:
    """Every job_url this profile has ever evaluated.

    `job_url` is the de-facto primary key throughout the codebase, and `evaluations.jsonl`
    is the complete record of what has been scored — so it doubles as the "have I seen this
    before?" index. No separate index file to keep in sync.
    """
    if not evaluations_path.exists():
        return set()
    return {rec["job"]["job_url"] for rec in read_jsonl(evaluations_path)}


def collect_unseen(
    queries: list[JobQuery],
    cfg: ProfileConfig,
    seen_urls: set[str],
) -> Harvest:
    """Scrape until `cfg.target_new_jobs` postings survive the screen and have never been
    evaluated before.

    Each round pages deeper (`offset += results_per_query`). The paging is the whole point:
    without it, day 2 re-scrapes page 1, finds every result already evaluated, and has
    nothing to do. With it, the agent keeps digging until it has a full batch.

    Screened-out postings do not consume a slot — the batch is `target_new_jobs` jobs worth
    *evaluating*, not `target_new_jobs` minus however many Directors in New York happened to
    turn up. They are also not remembered: re-screening them tomorrow is free, whereas
    evaluating them is not.
    """
    screen = Screen.from_config(cfg)
    seen = set(seen_urls)
    h = Harvest()

    for round_i in range(cfg.max_scrape_rounds):
        offset = round_i * cfg.results_per_query
        for query in queries:
            listings = fetch_jobs_for_query(
                query,
                cfg.results_per_query,
                offset=offset,
                hours_old=cfg.hours_old,
            )
            h.scraped += len(listings)

            for job in listings:
                if job.job_url in seen:
                    h.already_evaluated += 1
                    continue
                reason = screen.reject_reason(job)
                if reason is not None:
                    seen.add(job.job_url)  # don't re-screen it later in this same run
                    h.rejected[reason] += 1
                    continue
                seen.add(job.job_url)
                h.jobs.append(job)

            print(
                f"  round {round_i + 1}/{cfg.max_scrape_rounds} offset={offset:<3} "
                f"{query.search_term!r} -> {len(listings)} scraped, "
                f"{len(h.jobs)}/{cfg.target_new_jobs} to evaluate "
                f"({h.rejected_total} screened out, {h.already_evaluated} already done)"
            )

            if len(h.jobs) >= cfg.target_new_jobs:
                h.jobs = h.jobs[: cfg.target_new_jobs]
                return h
            time.sleep(INTER_SCRAPE_SLEEP)

    return h
