from __future__ import annotations

from job_search.config import settings
from job_search.data.sft_format import build_eval_sft, build_query_sft


def main() -> None:
    nq = build_query_sft()
    ne = build_eval_sft()
    print(f"wrote {nq} -> {settings.sft_dir / 'query_gen.jsonl'}")
    print(f"wrote {ne} -> {settings.sft_dir / 'fit_eval.jsonl'}")


if __name__ == "__main__":
    main()
