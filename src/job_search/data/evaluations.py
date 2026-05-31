from __future__ import annotations

from job_search.agents import evaluate_fit
from job_search.concurrency import map_to_jsonl
from job_search.config import settings
from job_search.io_utils import Record, read_jsonl
from job_search.providers import get_model
from job_search.schemas import JobListing


def _resume_texts_by_id() -> dict[int, str]:
    return {entry["id"]: entry["resume"] for entry in read_jsonl(settings.dataset1_path)}


async def build_eval_dataset() -> int:
    resumes = _resume_texts_by_id()
    model = get_model("deepseek")  # one shared client across concurrent calls

    pairs = [
        entry
        for entry in read_jsonl(settings.jobs_path)
        if entry["resume_id"] in resumes
    ][: settings.max_eval_pairs]

    async def work(entry: Record) -> Record | None:
        resume_id = entry["resume_id"]
        job = JobListing.model_validate(entry["job"])
        evaluation, reasoning = await evaluate_fit(resumes[resume_id], job, model=model)
        return {
            "resume_id": resume_id,
            "resume": resumes[resume_id],
            "job": job.model_dump(),
            "reasoning": reasoning,
            "evaluation": evaluation.model_dump(),
        }

    return await map_to_jsonl(
        pairs,
        work=work,
        out_path=settings.dataset2_path,
        item_key=lambda e: (e["resume_id"], e["job"]["job_url"]),
        record_key=lambda rec: (rec["resume_id"], rec["job"]["job_url"]),
        concurrency=settings.teacher_concurrency,
        request_pacing=settings.teacher_request_pacing,
        desc="Evaluating fit",
    )
