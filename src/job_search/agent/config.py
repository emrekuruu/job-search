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

    # --- Deterministic screen, applied before a posting reaches the evaluator ---------
    # These cost nothing and cannot be argued with, unlike the same rules written as prose
    # in `extra`. See agent/filters.py. All are case-insensitive regexes.
    #
    # Required, with no defaults: `[]` is a fine answer, but it should be one you chose —
    # a silently-empty screen is a screen you think is running and isn't.

    #: The posting's location must match at least ONE of these, or it's dropped. An
    #: allow-list, because the places a candidate *can't* work outnumber the ones they can.
    require_location_patterns: list[str]
    #: Matched against the TITLE only — seniority, contract type. Not the description,
    #: where "reports to the Director" would knock out a perfectly good junior role.
    exclude_title_patterns: list[str]
    #: Matched against title + description — the posting's language, stated requirements.
    exclude_text_patterns: list[str]

    # Search shape.
    n_queries: int = Field(gt=0)
    results_per_query: int = Field(gt=0)
    target_new_jobs: int = Field(gt=0)
    # How many times to page deeper (offset += results_per_query) hunting for unseen jobs
    # before giving up on this run.
    max_scrape_rounds: int = Field(gt=0)
    # Restrict to postings newer than N hours; None = no restriction.
    hours_old: int | None
