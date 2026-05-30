from __future__ import annotations

import random

from job_search.config import settings
from job_search.io_utils import Record, read_jsonl, write_jsonl
from job_search.prompts import (
    build_eval_system_prompt,
    build_eval_user,
    build_query_system_prompt,
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


def _split_and_write(records: list[Record], task: str) -> dict[str, int]:
    """Shuffle (seeded) and split into val/test/train, write three JSONL files.

    Order in the input is whatever the upstream curation produced (potentially
    sorted by resume id, category, etc.) — we shuffle deterministically so the
    train file does not feed examples in any natural ordering.
    """
    val_size = settings.val_size
    test_size = settings.test_size
    needed = val_size + test_size + 1  # at least one train example
    if len(records) < needed:
        raise ValueError(
            f"{task}: only {len(records)} records but need >= {needed} "
            f"(val={val_size} + test={test_size} + train>=1)"
        )

    rng = random.Random(settings.random_seed)
    rng.shuffle(records)

    val = records[:val_size]
    test = records[val_size : val_size + test_size]
    train = records[val_size + test_size :]

    n_train = write_jsonl(settings.sft_dir / f"{task}.train.jsonl", train)
    n_val = write_jsonl(settings.sft_dir / f"{task}.val.jsonl", val)
    n_test = write_jsonl(settings.sft_dir / f"{task}.test.jsonl", test)
    return {"train": n_train, "val": n_val, "test": n_test}


def build_query_sft() -> dict[str, int]:
    system = build_query_system_prompt()
    records: list[Record] = []
    for entry in read_jsonl(settings.dataset1_path):
        payload = QuerySet(queries=entry["queries"]).model_dump_json()
        records.append(
            _chat(
                system,
                build_query_user(entry["resume"], entry["category"]),
                _assistant(entry.get("reasoning"), payload),
            )
        )
    return _split_and_write(records, "query_gen")


def build_eval_sft() -> dict[str, int]:
    system = build_eval_system_prompt()
    records: list[Record] = []
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
    return _split_and_write(records, "fit_eval")
