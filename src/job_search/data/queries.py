from __future__ import annotations

from job_search.agents import generate_queries
from job_search.concurrency import map_to_jsonl
from job_search.config import settings
from job_search.data.resumes import Resume, load_resumes
from job_search.io_utils import Record
from job_search.providers import get_model


async def build_query_dataset() -> int:
    resumes = load_resumes()
    model = get_model("deepseek")  # one shared client across concurrent calls

    async def work(resume: Resume) -> Record | None:
        queryset, reasoning = await generate_queries(resume.text, resume.category, model=model)
        queries = [q.model_dump() for q in queryset.queries[: settings.max_queries_per_resume]]
        if not queries:
            return None
        return {
            "id": resume.id,
            "category": resume.category,
            "resume": resume.text,
            "reasoning": reasoning,
            "queries": queries,
        }

    return await map_to_jsonl(
        resumes,
        work=work,
        out_path=settings.dataset1_path,
        item_key=lambda r: r.id,
        record_key=lambda rec: rec["id"],
        concurrency=settings.teacher_concurrency,
        request_pacing=settings.teacher_request_pacing,
        desc="Generating queries",
    )
