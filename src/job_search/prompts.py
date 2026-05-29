from __future__ import annotations

from job_search.config import DIMENSIONS, MAX_TOTAL_SCORE, POINTS_PER_DIMENSION
from job_search.schemas import JobListing

QUERY_SYSTEM_PROMPT = f"""You are a job-search assistant. Given a candidate's resume, produce a small set of diverse LinkedIn job searches that would surface relevant openings.
Cover different angles: exact role titles, adjacent titles, key skills, and seniority. Set a location only when the resume clearly implies one; otherwise leave it null. Use is_remote and job_type only when justified by the resume.
Return distinct, non-redundant queries."""


def build_query_user(resume: str, category: str) -> str:
    return f"""Resume category: {category}

Resume:
{resume}"""


def build_eval_system_prompt() -> str:
    dimensions = "\n".join(
        f"  {i}. {dim.name} (0-{POINTS_PER_DIMENSION}): {dim.description}"
        for i, dim in enumerate(DIMENSIONS, 1)
    )
    return f"""You are an expert technical recruiter evaluating how well a candidate's resume fits a specific job posting.
Score the fit on exactly {len(DIMENSIONS)} dimensions, each worth {POINTS_PER_DIMENSION} points (total out of {MAX_TOTAL_SCORE}).
Dimensions (use these exact names, in this order):
{dimensions}
For each dimension give an integer score and a concise reasoning. The total must equal the sum of the dimension scores. Also give an overall_reasoning summarizing the fit."""


def build_eval_user(resume: str, job: JobListing) -> str:
    return f"""JOB POSTING
Title: {job.title}
Company: {job.company or "N/A"}
Location: {job.location or "N/A"}
Description:
{job.description}

CANDIDATE RESUME
{resume}"""
