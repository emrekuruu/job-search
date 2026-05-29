from __future__ import annotations

from job_search.config import settings
from job_search.data.evaluations import build_eval_dataset


def main() -> None:
    n = build_eval_dataset()
    print(f"wrote {n} evaluation records -> {settings.dataset2_path}")


if __name__ == "__main__":
    main()
