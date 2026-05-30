from __future__ import annotations

from job_search.config import DIMENSIONS, MAX_TOTAL_SCORE, POINTS_PER_DIMENSION, settings
from job_search.schemas import JobListing


def build_query_system_prompt(n: int | None = None) -> str:
    n = n if n is not None else settings.max_queries_per_resume
    return f"""You are a job-search assistant. Given a candidate's resume, produce exactly {n} LinkedIn job searches that would surface the most relevant openings.
Make them diverse and complementary:
- Anchor titles to the candidate's ACTUAL seniority — do not over- or under-shoot their level.
- Include exact and adjacent role titles, but make at least one or two queries anchored to the candidate's strongest specialization, industry, or signature skills (not title-only), so results are well-targeted rather than generic.
- Set a location only when the resume clearly implies one; otherwise leave it null. Use is_remote and job_type only when justified by the resume.
- If the candidate provides EXPLICIT preferences (job type, work modality, location), apply them to EVERY query — they take priority over resume signals. For modality: "remote" -> set is_remote=true; "hybrid" or "on-premise" -> embed the word in search_term and leave is_remote=false. For job_type, use the canonical JobSpy value (fulltime / parttime / contract / internship).
Return exactly {n} distinct, non-redundant queries."""


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

Score each dimension on this 0-{POINTS_PER_DIMENSION} scale, and use the FULL range — do not be artificially harsh:
  0-4    none / negligible match
  5-9    weak — major gaps
  10-14  moderate — partial fit with notable gaps
  15-18  strong — solid fit, only minor gaps
  19-20  ideal — fully meets or exceeds the requirement
For each dimension give an integer score and a concise, evidence-based reasoning that cites concrete facts from the resume and the job posting. The total must equal the sum of the dimension scores. Finally give an overall_reasoning summarizing the fit."""


def build_eval_user(resume: str, job: JobListing) -> str:
    return f"""JOB POSTING
Title: {job.title}
Company: {job.company or "N/A"}
Location: {job.location or "N/A"}
Description:
{job.description}

CANDIDATE RESUME
{resume}"""
