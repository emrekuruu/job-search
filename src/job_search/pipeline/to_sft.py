from __future__ import annotations

from job_search.config import settings
from job_search.data.sft_format import build_eval_sft, build_query_sft


def _print_split(task: str, counts: dict[str, int]) -> None:
    print(
        f"{task}: train={counts['train']} val={counts['val']} test={counts['test']} "
        f"-> {settings.sft_dir}/{task}.{{train,val,test}}.jsonl"
    )


def main() -> None:
    if settings.dataset1_path.exists():
        _print_split("query_gen", build_query_sft())
    else:
        print(f"skip query_gen: {settings.dataset1_path} not found")
    if settings.dataset2_path.exists():
        _print_split("fit_eval", build_eval_sft())
    else:
        print(f"skip fit_eval: {settings.dataset2_path} not found (run fetch-jobs + gen-evals)")
