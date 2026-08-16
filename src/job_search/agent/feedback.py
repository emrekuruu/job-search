"""Per-query performance, and the feedback block the query writer sees.

The agent's own scores and the user's star ratings (from the viewer's status.json) are
aggregated per search query. The viewer shows the table; the daily run appends a short
digest to the query writer's input so tomorrow's searches lean on what worked and drop
what didn't. Ratings are the ground truth when present; the model's mean score is the
weaker, always-available signal.
"""
from __future__ import annotations

from typing import Any

from job_search.schemas import JobQuery

# Records written before the agent recorded which query surfaced each posting.
UNATTRIBUTED = "Before query tracking (older runs)"

#: A query needs at least this many surfaced postings before it counts as evidence —
#: one lucky hit must not steer the whole search.
MIN_JOBS_FOR_FEEDBACK = 5


def _rating(status: dict[str, Any], url: str) -> int | None:
    value = status.get(url, {}).get("rating")
    return int(value) if value is not None else None


def query_label(rec: dict[str, Any]) -> str:
    if "query" not in rec:
        return UNATTRIBUTED
    q = JobQuery.model_validate(rec["query"])
    bits = [q.search_term]
    if q.location:
        bits.append(q.location)
    if q.is_remote:
        bits.append("remote")
    if q.job_type:
        bits.append(q.job_type)
    return " · ".join(bits)


def query_stats(records: list[dict[str, Any]], status: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per distinct query: postings surfaced, strong (70+), the model's mean score,
    applied count, and the user's mean rating with how many they rated. Sorted by user
    rating, then model score."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        groups.setdefault(query_label(rec), []).append(rec)

    rows: list[dict[str, Any]] = []
    for label, recs in groups.items():
        urls = [r["job"]["job_url"] for r in recs]
        ratings = [r for r in (_rating(status, u) for u in urls) if r]
        rows.append({
            "query": label,
            "jobs": len(recs),
            "strong": sum(1 for r in recs if r["evaluation"]["total"] >= 70),
            "avg_score": sum(r["evaluation"]["total"] for r in recs) / len(recs),
            "rated": len(ratings),
            "avg_rating": (sum(ratings) / len(ratings)) if ratings else None,
            "applied": sum(1 for u in urls if status.get(u, {}).get("applied")),
        })
    rows.sort(
        key=lambda r: (r["avg_rating"] if r["avg_rating"] is not None else -1, r["avg_score"]),
        reverse=True,
    )
    return rows


def build_query_feedback(records: list[dict[str, Any]], status: dict[str, Any]) -> str | None:
    """The block appended to the query writer's input, or None when there is no evidence
    yet (first runs, or nothing attributed to a query)."""
    rows = [
        r for r in query_stats(records, status)
        if r["query"] != UNATTRIBUTED and r["jobs"] >= MIN_JOBS_FOR_FEEDBACK
    ]
    if not rows:
        return None
    lines = []
    for r in rows:
        rating = (
            f"candidate rated {r['avg_rating']:.1f}/10 over {r['rated']} postings"
            if r["avg_rating"] is not None else "not yet rated by the candidate"
        )
        lines.append(
            f'- "{r["query"]}": {r["jobs"]} postings, mean fit score {r["avg_score"]:.0f}/100, '
            f"{r['strong']} strong (70+), {r['applied']} applied; {rating}"
        )
    return (
        "PAST SEARCH PERFORMANCE (from previous runs, best first). The candidate's own "
        "rating is the ground truth; the fit score is this system's estimate.\n"
        + "\n".join(lines)
        + "\nUse this: keep or sharpen the angles that scored well, reformulate or drop the "
        "ones that scored poorly, and make at least one query a genuinely new angle not "
        "listed above so the search keeps exploring."
    )
