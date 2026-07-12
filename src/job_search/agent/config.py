from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProfileConfig(BaseModel):
    """One search track: `profiles/<id>/config.json` in the bucket.

    Every field is required. A profile is a *role track* — `gf-data-analyst`,
    `gf-product`, `emre-ml` — not a person, so one human can run several. There are no
    defaults on purpose: a silently-defaulted search is a search that quietly looked for
    the wrong thing.
    """

    model_config = ConfigDict(extra="forbid")

    # Feeds `prompts.build_query_user(resume, category)` — the lever that makes each
    # profile hunt for a different kind of role off the same machinery.
    category: str

    # Candidate preferences. Mirror the interactive Space's controls; `job_type` and
    # `modality` accept the same labels (see job_search.preferences), `None` = no
    # preference. `location` is free text.
    job_type: str | None
    modality: str | None
    location: str | None
    extra: str | None

    # Search shape.
    n_queries: int = Field(gt=0)
    results_per_query: int = Field(gt=0)
    target_new_jobs: int = Field(gt=0)
    # How many times to page deeper (offset += results_per_query) hunting for unseen jobs
    # before giving up on this run.
    max_scrape_rounds: int = Field(gt=0)
    # Restrict to postings newer than N hours; None = no restriction.
    hours_old: int | None
