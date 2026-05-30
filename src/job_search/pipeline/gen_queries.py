from __future__ import annotations

import asyncio

from job_search.config import settings
from job_search.data.queries import build_query_dataset


def main() -> None:
    n = asyncio.run(build_query_dataset())
    print(f"wrote {n} new query records -> {settings.dataset1_path}")


if __name__ == "__main__":
    main()
