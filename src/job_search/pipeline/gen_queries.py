from __future__ import annotations

from job_search.config import settings
from job_search.data.queries import build_query_dataset


def main() -> None:
    n = build_query_dataset()
    print(f"wrote {n} query records -> {settings.dataset1_path}")


if __name__ == "__main__":
    main()
