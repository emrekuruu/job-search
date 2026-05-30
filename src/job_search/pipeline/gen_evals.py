from __future__ import annotations

import asyncio

from job_search.config import settings
from job_search.data.evaluations import build_eval_dataset


def main() -> None:
    n = asyncio.run(build_eval_dataset())
    print(f"wrote {n} new evaluation records -> {settings.dataset2_path}")


if __name__ == "__main__":
    main()
