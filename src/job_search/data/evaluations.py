from __future__ import annotations

from job_search.agents import evaluate_fit
from job_search.config import settings
from job_search.io_utils import read_jsonl, write_jsonl
from job_search.schemas import JobListing


def _resume_texts_by_id() -> dict[int, str]:
    return {entry["id"]: entry["resume"] for entry in read_jsonl(settings.dataset1_path)}


def build_eval_dataset() -> int:
    resumes = _resume_texts_by_id()

    records = []
    for entry in read_jsonl(settings.jobs_path):
        if len(records) >= settings.max_eval_pairs:
            break
        resume_id = entry["resume_id"]
        resume_text = resumes.get(resume_id)
        if resume_text is None:
            continue
        job = JobListing.model_validate(entry["job"])
        evaluation, reasoning = evaluate_fit(resume_text, job)
        records.append(
            {
                "resume_id": resume_id,
                "resume": resume_text,
                "job": job.model_dump(),
                "reasoning": reasoning,
                "evaluation": evaluation.model_dump(),
            }
        )

    return write_jsonl(settings.dataset2_path, records)
