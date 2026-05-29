from __future__ import annotations

from job_search.agents import generate_queries
from job_search.config import settings
from job_search.data.resumes import load_resumes
from job_search.io_utils import write_jsonl


def build_query_dataset() -> int:
    resumes = load_resumes()

    records = []
    for resume in resumes:
        queryset, reasoning = generate_queries(resume.text, resume.category)
        queries = [q.model_dump() for q in queryset.queries[: settings.max_queries_per_resume]]
        if not queries:
            continue
        records.append(
            {
                "id": resume.id,
                "category": resume.category,
                "resume": resume.text,
                "reasoning": reasoning,
                "queries": queries,
            }
        )

    return write_jsonl(settings.dataset1_path, records)
