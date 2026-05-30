from __future__ import annotations

import html

from job_search.schemas import FitEvaluation, JobListing, JobQuery


def _score_band(score: int) -> str:
    """Return 'high' / 'mid' / 'low' — drives both the badge gradient and the card accent."""
    if score >= 80:
        return "high"
    if score >= 60:
        return "mid"
    return "low"


def render_job_card(job: JobListing, evaluation: FitEvaluation) -> str:
    band = _score_band(evaluation.total)
    title = html.escape(job.title)
    company = html.escape(job.company or "Unknown company")
    location = html.escape(job.location or "Location not listed")
    url = html.escape(job.job_url)
    overall = html.escape(evaluation.overall_reasoning)

    dim_rows = "".join(
        f"""<tr>
                <td class="dim-name">{html.escape(d.name.replace("_", " ").title())}</td>
                <td class="dim-score">{d.score}/20</td>
                <td>{html.escape(d.reasoning)}</td>
            </tr>"""
        for d in evaluation.dimensions
    )

    return f"""
    <div class="job-card score-{band}">
        <div class="card-accent"></div>
        <span class="score-badge score-{band}">
            {evaluation.total}<small>/100</small>
        </span>
        <h3>{title}</h3>
        <div class="meta">
            <strong>{company}</strong> &middot; {location} &middot;
            <a href="{url}" target="_blank" rel="noopener">View on LinkedIn ↗</a>
        </div>
        <div class="overall">{overall}</div>
        <details>
            <summary>Dimension breakdown ({len(evaluation.dimensions)} dimensions)</summary>
            <table class="dim-table">
                <tbody>{dim_rows}</tbody>
            </table>
        </details>
    </div>
    """


def render_query_chip(search_term: str) -> str:
    return f'<span class="query-chip">{html.escape(search_term)}</span>'


def render_query_card(query: JobQuery) -> str:
    """A richer query view: search term in heading position + metadata pills below."""
    pills: list[str] = []
    if query.location:
        pills.append(
            f'<span class="qpill qpill-loc">'
            f'<span class="qpill-icon">📍</span>{html.escape(query.location)}</span>'
        )
    if query.is_remote:
        pills.append(
            '<span class="qpill qpill-remote">'
            '<span class="qpill-icon">🌐</span>Remote</span>'
        )
    if query.job_type:
        pills.append(
            f'<span class="qpill qpill-type">'
            f'<span class="qpill-icon">💼</span>{html.escape(query.job_type)}</span>'
        )

    meta_html = (
        f'<div class="query-meta">{"".join(pills)}</div>' if pills else ""
    )

    return f"""
    <div class="query-card">
        <div class="query-term">
            <span class="query-term-icon">🔍</span>
            <span class="query-term-text">{html.escape(query.search_term)}</span>
        </div>
        {meta_html}
    </div>
    """
