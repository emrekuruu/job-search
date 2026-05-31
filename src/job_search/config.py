from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Dimension(BaseModel):
    """One scoring dimension for the resume-vs-job fit evaluation (worth 20 pts)."""

    name: str
    description: str


# PLACEHOLDER dimensions. TODO: research and replace with the real 5 dimensions.
# Each is worth 20 points; five dimensions => 100 points total.
DIMENSIONS: list[Dimension] = [
    Dimension(
        name="skills_match",
        description="How well the candidate's hard/technical skills match the role's requirements.",
    ),
    Dimension(
        name="experience_relevance",
        description="Relevance and depth of prior work experience to the target role.",
    ),
    Dimension(
        name="education_certifications",
        description="Fit of education, degrees, and certifications to the role's expectations.",
    ),
    Dimension(
        name="industry_domain_fit",
        description="Alignment of the candidate's industry/domain background with the job.",
    ),
    Dimension(
        name="seniority_role_alignment",
        description="Match between the candidate's seniority level and the role's seniority.",
    ),
]

POINTS_PER_DIMENSION = 20
MAX_TOTAL_SCORE = POINTS_PER_DIMENSION * len(DIMENSIONS)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Teacher (data generation): DeepSeek V4 Pro, top reasoning/agentic model ---
    deepseek_api_key: str | None = None
    teacher_model: str = "deepseek-v4-pro"

    # Teacher request controls (per-call generation settings)
    teacher_temperature: float = 1.0
    teacher_max_tokens: int = 16_000
    teacher_timeout: float = 600.0  # seconds; reasoning calls are slow

    # Concurrency + rate-limit resilience for teacher calls.
    # DeepSeek v4-pro caps account-wide concurrency at 500; 200 leaves headroom for retries.
    teacher_concurrency: int = 200
    teacher_max_retries: int = 5
    teacher_retry_base_delay: float = 2.0  # exponential backoff base, seconds
    teacher_request_pacing: float = 0.5    # per-call hold (seconds) to smooth the request rate

    # --- Start-small knobs ---
    resume_sample_size: int | None = None  # None = use the entire dataset; set an int to sample
    max_queries_per_resume: int = 4
    jobs_per_query: int = 5
    jobs_concurrency: int = 10  # parallel LinkedIn scrapes per fetch-jobs run
    max_job_queries: int | None = None  # cap total queries scraped (None = all); for smoke tests
    max_eval_pairs: int | None = None  # cap eval pairs / teacher calls (None = evaluate all jobs)
    max_resume_chars: int = 12_000
    random_seed: int = 42

    # --- SFT train/val/test split (applied in sft_format.py) ---
    val_size: int = 300
    test_size: int = 300

    # --- Paths ---
    data_dir: Path = _PROJECT_ROOT / "data"

    @property
    def resumes_path(self) -> Path:
        return self.data_dir / "resumes_sample.jsonl"

    @property
    def dataset1_path(self) -> Path:
        return self.data_dir / "dataset1.jsonl"

    @property
    def jobs_path(self) -> Path:
        return self.data_dir / "jobs.jsonl"

    @property
    def dataset2_path(self) -> Path:
        return self.data_dir / "dataset2.jsonl"

    @property
    def sft_dir(self) -> Path:
        return self.data_dir / "sft"


settings = Settings()
