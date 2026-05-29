from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from job_search.config import DIMENSIONS, MAX_TOTAL_SCORE, POINTS_PER_DIMENSION

_DIMENSION_NAMES = [d.name for d in DIMENSIONS]


class JobQuery(BaseModel):
    """A single LinkedIn job search. Maps directly to JobSpy parameters."""

    search_term: str = Field(description="Keywords / role title to search for.")
    location: str | None = Field(
        default=None, description="Geographic location, or null for anywhere."
    )
    is_remote: bool = Field(default=False, description="Restrict to remote roles.")
    job_type: str | None = Field(
        default=None,
        description="One of fulltime, parttime, internship, contract, or null.",
    )


class QuerySet(BaseModel):
    """A set of LinkedIn searches generated from a resume.

    Used as the query agent's output_type so the serialized SFT target is a clean
    JSON object (`{"queries": [...]}`) rather than a bare array.
    """

    queries: list[JobQuery]


class JobListing(BaseModel):
    """A job posting returned by the retrieval step."""

    title: str
    company: str | None = None
    location: str | None = None
    description: str
    job_url: str


class DimensionScore(BaseModel):
    """Score and rationale for one fit dimension (0..20)."""

    name: str
    score: int = Field(ge=0, le=POINTS_PER_DIMENSION)
    reasoning: str


class FitEvaluation(BaseModel):
    """Resume-vs-job fit across the configured dimensions (total out of 100)."""

    dimensions: list[DimensionScore]
    total: int = Field(ge=0, le=MAX_TOTAL_SCORE)
    overall_reasoning: str

    @model_validator(mode="after")
    def _check(self) -> "FitEvaluation":
        if len(self.dimensions) != len(_DIMENSION_NAMES):
            raise ValueError(
                f"expected {len(_DIMENSION_NAMES)} dimensions, got {len(self.dimensions)}"
            )
        names = [d.name for d in self.dimensions]
        if names != _DIMENSION_NAMES:
            raise ValueError(f"dimension names {names} != configured {_DIMENSION_NAMES}")
        summed = sum(d.score for d in self.dimensions)
        if summed != self.total:
            raise ValueError(f"total {self.total} != sum of dimension scores {summed}")
        return self
