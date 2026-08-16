"""Pure HTML rendering for the results viewer.

Everything the user sees below the toolbar is ONE string produced here and handed to a
single ``gr.HTML``. That is the whole reason the viewer is stable: a profile with 800
evaluations used to become 800 x (HTML + 2 Checkboxes + 2 event listeners) Gradio
components per render, which is what OOM'd the free box and tripped Gradio's re-render
races. Now a page is 20 cards of plain markup regardless of how many records exist.
"""
from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from job_search.agent.feedback import query_stats
from job_search.schemas import FitEvaluation, JobListing

PAGE_SIZE = 20

SORT_BEST = "Best match"
SORT_NEWEST = "Newest first"
SORT_CHOICES = [SORT_BEST, SORT_NEWEST]

DEFAULT_MIN_SCORE = 50
MAX_RATING = 10
# (label, value) for the toolbar dropdown. Low scores exist in the file but are noise for
# a daily skim, hence the default floor.
MIN_SCORE_CHOICES = [
    ("Any score", 0), ("30+", 30), ("50+", 50), ("60+", 60), ("70+", 70), ("80+", 80),
]


def _band(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 50:
        return "mid"
    return "low"


def _added_label(saved_at: str) -> str:
    dt = datetime.strptime(saved_at, "%Y-%m-%dT%H:%M:%SZ")
    return f"{dt.day} {dt:%b %Y}"


# ---- filtering / sorting / paging -------------------------------------------------------


def _is_applied(status: dict[str, Any], url: str) -> bool:
    return bool(status.get(url, {}).get("applied", False))


def _rating(status: dict[str, Any], url: str) -> int | None:
    """The user's 1..10 stars, or None if they haven't rated this posting."""
    value = status.get(url, {}).get("rating")
    return int(value) if value is not None else None


def sort_records(records: list[dict[str, Any]], how: str) -> list[dict[str, Any]]:
    """Best match = score desc, ties broken by newest. Newest = the reverse."""
    if how == SORT_NEWEST:
        key = lambda r: (r["saved_at"], r["evaluation"]["total"])  # noqa: E731
    elif how == SORT_BEST:
        key = lambda r: (r["evaluation"]["total"], r["saved_at"])  # noqa: E731
    else:
        raise ValueError(f"Unknown sort {how!r}; expected one of {SORT_CHOICES}")
    return sorted(records, key=key, reverse=True)


def select_records(
    records: list[dict[str, Any]],
    status: dict[str, Any],
    *,
    min_score: int,
    hide_rated: bool,
    sort: str,
) -> list[dict[str, Any]]:
    """Apply the toolbar: score floor, hide-rated (rated = already looked at), then sort."""
    out: list[dict[str, Any]] = []
    for rec in records:
        if rec["evaluation"]["total"] < min_score:
            continue
        url = rec["job"]["job_url"]
        if hide_rated and _rating(status, url) and not _is_applied(status, url):
            continue
        out.append(rec)
    return sort_records(out, sort)


def page_count(n_records: int) -> int:
    return max(1, -(-n_records // PAGE_SIZE))


def clamp_page(page: int, n_records: int) -> int:
    return min(max(1, page), page_count(n_records))


def page_slice(records: list[dict[str, Any]], page: int) -> list[dict[str, Any]]:
    start = (page - 1) * PAGE_SIZE
    return records[start : start + PAGE_SIZE]


# ---- markup -----------------------------------------------------------------------------


def render_summary(records: list[dict[str, Any]], status: dict[str, Any]) -> str:
    total = len(records)
    rated = sum(1 for r in records if _rating(status, r["job"]["job_url"]))
    applied = sum(1 for r in records if _is_applied(status, r["job"]["job_url"]))
    strong = sum(1 for r in records if r["evaluation"]["total"] >= 70)
    return (
        '<div class="rv-stats">'
        f'<div class="rv-stat"><span class="rv-stat-n">{total}</span><span class="rv-stat-l">evaluated</span></div>'
        f'<div class="rv-stat"><span class="rv-stat-n">{strong}</span><span class="rv-stat-l">strong (70+)</span></div>'
        f'<div class="rv-stat"><span class="rv-stat-n">{rated}</span><span class="rv-stat-l">rated</span></div>'
        f'<div class="rv-stat"><span class="rv-stat-n">{applied}</span><span class="rv-stat-l">applied</span></div>'
        "</div>"
    )


def _stars(url: str, rating: int | None) -> str:
    """Ten clickable stars. `data-field="rating"` rides the same change bridge as the
    ticks; the JS turns a star click into {field: "rating", value: n}."""
    filled = rating or 0
    stars = "".join(
        f'<button type="button" class="rv-star{" on" if i <= filled else ""}" '
        f'data-url="{url}" data-field="rating" data-value="{i}" '
        f'aria-label="{i} of {MAX_RATING}">★</button>'
        for i in range(1, MAX_RATING + 1)
    )
    label = f"{rating}/{MAX_RATING}" if rating else "Rate it"
    return (
        f'<span class="rv-rating" data-rated="{int(bool(rating))}">'
        f'{stars}<span class="rv-rating-label">{label}</span></span>'
    )


def _tick(url: str, field: str, checked: bool, label: str) -> str:
    return (
        f'<label class="rv-tick rv-tick-{field}">'
        f'<input type="checkbox" data-url="{url}" data-field="{field}"'
        f'{" checked" if checked else ""}>'
        f"<span>{label}</span></label>"
    )


def render_card(rec: dict[str, Any], status: dict[str, Any]) -> str:
    job = JobListing.model_validate(rec["job"])
    ev = FitEvaluation.model_validate(rec["evaluation"])
    applied = _is_applied(status, job.job_url)
    rating = _rating(status, job.job_url)
    band = _band(ev.total)
    query = (
        f'<span class="rv-dot">·</span><span class="rv-query" title="Query that found it">'
        f'🔍 {html.escape(rec["query"]["search_term"])}</span>'
        if "query" in rec else ""
    )
    url = html.escape(job.job_url, quote=True)

    dims = "".join(
        '<li class="rv-dim">'
        f'<div class="rv-dim-head"><span>{html.escape(d.name.replace("_", " ").title())}</span>'
        f'<span class="rv-dim-score">{d.score}<small>/20</small></span></div>'
        f'<div class="rv-dim-bar"><i style="width:{d.score * 5}%"></i></div>'
        f'<p>{html.escape(d.reasoning)}</p></li>'
        for d in ev.dimensions
    )

    state_cls = " is-applied" if applied else (" is-rated" if rating else "")
    return f"""
<article class="rv-card band-{band}{state_cls}">
  <div class="rv-score"><b>{ev.total}</b><small>/100</small></div>
  <div class="rv-body">
    <header>
      <h3><a href="{url}" target="_blank" rel="noopener">{html.escape(job.title)}</a></h3>
      <div class="rv-meta">
        <span class="rv-company">{html.escape(job.company or "Unknown company")}</span>
        <span class="rv-dot">·</span>
        <span>{html.escape(job.location or "Location not listed")}</span>
        <span class="rv-dot">·</span>
        <span class="rv-added">Added {_added_label(rec["saved_at"])}</span>
        {query}
      </div>
    </header>
    <p class="rv-reasoning">{html.escape(ev.overall_reasoning)}</p>
    <details class="rv-details">
      <summary>Score breakdown</summary>
      <ul class="rv-dims">{dims}</ul>
    </details>
    <div class="rv-actions">
      {_tick(url, "applied", applied, "Applied")}
      {_stars(url, rating)}
      <a class="rv-open" href="{url}" target="_blank" rel="noopener">Open posting ↗</a>
    </div>
  </div>
</article>"""


def render_empty(*, has_records: bool) -> str:
    if not has_records:
        return (
            '<div class="rv-empty"><h3>No evaluations yet</h3>'
            "<p>The agent hasn't completed a run for this profile. "
            "Check back after the next scheduled search.</p></div>"
        )
    return (
        '<div class="rv-empty"><h3>Nothing matches these filters</h3>'
        "<p>Lower the minimum score or untick <em>Hide rated</em>.</p></div>"
    )


def render_page(
    page_records: list[dict[str, Any]], status: dict[str, Any], *, has_records: bool
) -> str:
    if not page_records:
        return render_empty(has_records=has_records)
    return '<div class="rv-list">' + "".join(
        render_card(r, status) for r in page_records
    ) + "</div>"


def page_label(page: int, n_selected: int) -> str:
    if n_selected == 0:
        return "No results"
    lo = (page - 1) * PAGE_SIZE + 1
    hi = min(page * PAGE_SIZE, n_selected)
    return f"{lo}–{hi} of {n_selected} · page {page}/{page_count(n_selected)}"


# ---- queries ------------------------------------------------------------------------------


def render_query_stats(records: list[dict[str, Any]], status: dict[str, Any]) -> str:
    rows = query_stats(records, status)
    if not rows:
        return '<div class="rv-empty"><h3>No queries yet</h3><p>Stats appear once the agent has run.</p></div>'
    body = ""
    for r in rows:
        rating = f"{r['avg_rating']:.1f}" if r["avg_rating"] is not None else "—"
        bar = int(round((r["avg_rating"] or 0) * 10))
        body += (
            "<tr>"
            f'<td class="rv-q-name">{html.escape(r["query"])}</td>'
            f'<td class="num">{r["jobs"]}</td>'
            f'<td class="num">{r["strong"]}</td>'
            f'<td class="num">{r["avg_score"]:.0f}</td>'
            f'<td class="num">{r["applied"]}</td>'
            f'<td class="num rv-q-rating"><span class="rv-q-bar"><i style="width:{bar}%"></i></span>'
            f'{rating}<small> ({r["rated"]} rated)</small></td>'
            "</tr>"
        )
    return (
        '<div class="rv-table-wrap"><table class="rv-table"><thead><tr>'
        "<th>Query</th><th>Jobs</th><th>Strong (70+)</th><th>Avg model score</th>"
        "<th>Applied</th><th>Your rating /10</th>"
        f"</tr></thead><tbody>{body}</tbody></table></div>"
    )
