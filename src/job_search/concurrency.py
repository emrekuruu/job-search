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
    request_pacing: float = 0.0,
) -> int:
    """Run `work` over `items` concurrently, appending each result to `out_path` as it lands.

    - Bounded by `concurrency` in-flight tasks (avoids overwhelming the API / rate limits).
    - Incremental + crash-safe: each record is written and flushed under a lock as soon as
      it completes, so partial progress survives interruption.
    - Resumable: items whose `item_key` already appears in `out_path` are skipped, so a
      re-run continues where a rate-limited / interrupted run left off.
    - Per-item failure-tolerant: exceptions from `work(item)` are logged and that item is
      skipped — other workers keep going. Failed items remain "pending" on the next run.
    - `request_pacing > 0` holds each semaphore slot for that many extra seconds after the
      call completes, smoothing the steady-state request rate so the API isn't slammed.

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
    failed = 0

    with out_path.open("a", encoding="utf-8") as f, tqdm(
        total=len(pending), desc=desc, unit="item"
    ) as pbar:

        async def worker(item: T) -> None:
            nonlocal written, failed
            record: Record | None = None
            async with sem:
                try:
                    record = await work(item)
                except Exception as e:
                    failed += 1
                    tqdm.write(
                        f"[skip] {item_key(item)}: {type(e).__name__}: {e}"
                    )
                if request_pacing > 0:
                    await asyncio.sleep(request_pacing)
            if record is not None:
                async with write_lock:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f.flush()
                    written += 1
            pbar.update(1)
            pbar.set_postfix(written=written, failed=failed)

        await asyncio.gather(*(worker(it) for it in pending))

    return written
