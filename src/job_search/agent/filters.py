from __future__ import annotations

import re
from dataclasses import dataclass

from job_search.agent.config import ProfileConfig
from job_search.schemas import JobListing


@dataclass(frozen=True)
class Screen:
    """Deterministic disqualifiers, applied *before* a posting reaches the evaluator.

    Prose in the prompt asks the model to reject things; a regex makes it so. The model is
    good at judging fit and unreliable at obeying hard rules — it will happily award a
    strong skills match to a Director role in New York and score it 78. Anything that is a
    yes/no fact about the posting (its city, its language, its contract type) belongs here,
    where it costs nothing and cannot be talked out of. Only genuine judgement is left to
    the model.
    """

    require_location: list[re.Pattern[str]]
    exclude_title: list[re.Pattern[str]]
    exclude_text: list[re.Pattern[str]]

    @classmethod
    def from_config(cls, cfg: ProfileConfig) -> "Screen":
        c = lambda pats: [re.compile(p, re.IGNORECASE) for p in pats]  # noqa: E731
        return cls(
            require_location=c(cfg.require_location_patterns),
            exclude_title=c(cfg.exclude_title_patterns),
            exclude_text=c(cfg.exclude_text_patterns),
        )

    def reject_reason(self, job: JobListing) -> str | None:
        """Why this posting is disqualified, or None to let it through to the evaluator."""
        # 1. Geography. An allow-list, not a block-list: everywhere the candidate cannot
        #    work is a much longer list than everywhere they can.
        if self.require_location:
            where = job.location or ""
            if not any(p.search(where) for p in self.require_location):
                return f"location {where!r} matches no allowed location"

        # 2. Title. Seniority and contract type live here. Deliberately NOT matched against
        #    the description: "reports to the Director" would knock out a perfectly good
        #    junior role.
        for p in self.exclude_title:
            if p.search(job.title):
                return f"title matches /{p.pattern}/"

        # 3. Full text. Language of the posting, stated requirements.
        haystack = f"{job.title}\n{job.description}"
        for p in self.exclude_text:
            if p.search(haystack):
                return f"text matches /{p.pattern}/"

        return None
