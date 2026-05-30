from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Hashable, Iterable
from pathlib import Path
from typing import TypeVar

from tqdm import tqdm

from job_search.io_utils import Record, read_jsonl

T = TypeVar("T")


async def map_to_jsonl(
    items: Iterable[T],
    *,
    work: Callable[[T], Awaitable[Record | None]],
    out_path: Path,
    item_key: Callable[[T], Hashable],
    record_key: Callable[[Record], Hashable],
    concurrency: int,
    desc: str,
) -> int:
    """Run `work` over `items` concurrently, appending each result to `out_path` as it lands.

    - Bounded by `concurrency` in-flight tasks (avoids overwhelming the API / rate limits).
    - Incremental + crash-safe: each record is written and flushed under a lock as soon as
      it completes, so partial progress survives interruption.
    - Resumable: items whose `item_key` already appears in `out_path` are skipped, so a
      re-run continues where a rate-limited / interrupted run left off.
    Returns the number of new records written this run.
    """
    items = list(items)
    done: set[Hashable] = set()
    if out_path.exists():
        done = {record_key(rec) for rec in read_jsonl(out_path)}
    pending = [it for it in items if item_key(it) not in done]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()
    written = 0

    with out_path.open("a", encoding="utf-8") as f, tqdm(
        total=len(pending), desc=desc, unit="item"
    ) as pbar:

        async def worker(item: T) -> None:
            nonlocal written
            async with sem:
                record = await work(item)
            if record is not None:
                async with write_lock:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f.flush()
                    written += 1
            pbar.update(1)

        await asyncio.gather(*(worker(it) for it in pending))

    return written
