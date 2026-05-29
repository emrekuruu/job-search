from __future__ import annotations

from job_search.config import settings
from job_search.io_utils import read_jsonl, write_jsonl
from job_search.prompts import (
    QUERY_SYSTEM_PROMPT,
    build_eval_system_prompt,
    build_eval_user,
    build_query_user,
)
from job_search.schemas import FitEvaluation, JobListing, QuerySet


def _assistant(reasoning: str | None, payload_json: str) -> str:
    reasoning = (reasoning or "").strip()
    if reasoning:
        return f"<think>\n{reasoning}\n</think>\n\n{payload_json}"
    return payload_json


def _chat(system: str, user: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


def build_query_sft() -> int:
    records = []
    for entry in read_jsonl(settings.dataset1_path):
        payload = QuerySet(queries=entry["queries"]).model_dump_json()
        records.append(
            _chat(
                QUERY_SYSTEM_PROMPT,
                build_query_user(entry["resume"], entry["category"]),
                _assistant(entry.get("reasoning"), payload),
            )
        )
    return write_jsonl(settings.sft_dir / "query_gen.jsonl", records)


def build_eval_sft() -> int:
    system = build_eval_system_prompt()
    records = []
    for entry in read_jsonl(settings.dataset2_path):
        job = JobListing.model_validate(entry["job"])
        payload = FitEvaluation.model_validate(entry["evaluation"]).model_dump_json()
        records.append(
            _chat(
                system,
                build_eval_user(entry["resume"], job),
                _assistant(entry.get("reasoning"), payload),
            )
        )
    return write_jsonl(settings.sft_dir / "fit_eval.jsonl", records)
