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

    # --- Student (training + serving) ---
    student_model: str = "Qwen/Qwen3.5-9B"
    hf_token: str | None = None
    vllm_api_base: str | None = None
    vllm_api_key: str = "EMPTY"

    # --- Start-small knobs ---
    resume_sample_size: int = 30
    max_queries_per_resume: int = 4
    jobs_per_query: int = 5
    max_eval_pairs: int = 60
    max_resume_chars: int = 12_000
    random_seed: int = 7

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
