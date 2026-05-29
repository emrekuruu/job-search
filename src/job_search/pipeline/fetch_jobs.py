from __future__ import annotations

from job_search.config import settings
from job_search.data.jobs import build_jobs_dataset


def main() -> None:
    n = build_jobs_dataset()
    print(f"wrote {n} job records -> {settings.jobs_path}")


if __name__ == "__main__":
    main()
