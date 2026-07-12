from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gradio as gr

from job_search import store
from job_search.io_utils import read_jsonl
from job_search.schemas import FitEvaluation, JobListing
from job_search.spaces.common.cards import render_job_card
from job_search.spaces.common.theme import CSS, theme
from job_search.store import ProfileStore

# Which bucket this viewer reads. Set as a Space *variable* (not a secret) at deploy time.
BUCKET_ENV = "JOB_AGENT_BUCKET"


def _bucket() -> str:
    bucket = os.environ.get(BUCKET_ENV)
    if not bucket:
        raise RuntimeError(
            f"{BUCKET_ENV} is not set; the viewer has no bucket to read. "
            "Set it as a Space variable, e.g. emrekuruu/job-agent."
        )
    return bucket


SORT_BEST = "Best match"
SORT_NEWEST = "Newest first"
SORT_CHOICES = [SORT_BEST, SORT_NEWEST]


def sort_records(records: list[dict[str, Any]], how: str) -> list[dict[str, Any]]:
    """Best match = score desc, ties broken by newest. Newest = the reverse."""
    if how == SORT_NEWEST:
        key = lambda r: (r["saved_at"], r["evaluation"]["total"])  # noqa: E731
    else:
        key = lambda r: (r["evaluation"]["total"], r["saved_at"])  # noqa: E731
    return sorted(records, key=key, reverse=True)


def load_profile(profile: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch one profile's evaluations (ranked, best first) and its reviewed/applied ticks."""
    ps = ProfileStore(_bucket(), profile)
    names = ps.list_names()
    if store.CONFIG not in names:
        raise ValueError(f"No profile named {profile!r} in this bucket.")

    with tempfile.TemporaryDirectory(prefix="job-viewer-") as tmp:
        workdir = Path(tmp)
        evaluations_path = workdir / store.EVALUATIONS
        if not ps.download_optional(store.EVALUATIONS, evaluations_path):
            # The profile exists but the agent hasn't had a successful run yet.
            return [], {}
        records = list(read_jsonl(evaluations_path))
        status = ps.read_json_optional(store.STATUS, workdir)

    return sort_records(records, SORT_BEST), status


def save_status(profile: str, status: dict[str, Any]) -> None:
    """Persist the ticks. The viewer owns `status.json` outright — the agent never writes it,
    so this can't race the nightly run."""
    ProfileStore(_bucket(), profile).write_json(store.STATUS, status)


def _summary(records: list[dict[str, Any]], status: dict[str, Any]) -> str:
    total = len(records)
    reviewed = sum(1 for r in records if status.get(r["job"]["job_url"], {}).get("reviewed"))
    applied = sum(1 for r in records if status.get(r["job"]["job_url"], {}).get("applied"))
    return (
        f'<div class="section-label">'
        f"{total} matches &middot; {reviewed} reviewed &middot; {applied} applied"
        f"</div>"
    )


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Your Matches") as demo:
        gr.HTML(
            '<div id="aurora-bg">'
            '  <div class="aurora-blob aurora-1"></div>'
            '  <div class="aurora-blob aurora-2"></div>'
            '  <div class="aurora-blob aurora-3"></div>'
            "</div>"
        )

        profile_state = gr.State("")
        jobs_state = gr.State([])
        status_state = gr.State({})

        with gr.Column(elem_id="hero"):
            gr.Markdown("# Your Matches")
            gr.Markdown("Every job your agent found, scored, and explained — freshest first.")

        # ---- Profile gate
        with gr.Column(visible=True, elem_classes=["profile-gate"]) as gate:
            with gr.Group(elem_classes=["glass-panel"]):
                profile_input = gr.Textbox(
                    label="Profile",
                    placeholder="e.g. gf-data-analyst",
                    autofocus=True,
                )
                load_btn = gr.Button("Open", variant="primary")
            gate_error = gr.Markdown(visible=False)

        # ---- Results
        with gr.Column(visible=False) as results_section:
            with gr.Row():
                summary_html = gr.HTML()
                sort_by = gr.Dropdown(
                    choices=SORT_CHOICES,
                    value=SORT_BEST,
                    label="Sort by",
                    scale=0,
                    min_width=170,
                )
                hide_done = gr.Checkbox(label="Hide reviewed", value=False, scale=0)
                switch_btn = gr.Button("Switch profile", scale=0)

            @gr.render(inputs=[jobs_state, status_state, hide_done, profile_state, sort_by])
            def render_jobs(
                records: list[dict[str, Any]],
                status: dict[str, Any],
                hide: bool,
                profile: str,
                how: str,
            ) -> None:
                if not records:
                    gr.Markdown(
                        "No evaluations yet — the agent hasn't completed a run for this "
                        "profile. Check back after tomorrow's search."
                    )
                    return

                shown = 0
                for rec in sort_records(records, how):
                    job = JobListing.model_validate(rec["job"])
                    evaluation = FitEvaluation.model_validate(rec["evaluation"])
                    st = status.get(job.job_url, {})
                    reviewed = bool(st.get("reviewed", False))
                    applied = bool(st.get("applied", False))
                    if hide and reviewed and not applied:
                        continue
                    shown += 1

                    with gr.Group():
                        gr.HTML(
                            render_job_card(
                                job,
                                evaluation,
                                reviewed=reviewed,
                                applied=applied,
                                saved_at=rec["saved_at"],
                            )
                        )
                        with gr.Row(elem_classes=["job-row-actions"]):
                            reviewed_box = gr.Checkbox(label="Reviewed", value=reviewed)
                            applied_box = gr.Checkbox(label="Applied", value=applied)

                    # Bind the row's url into the handler; `profile` comes from state so a
                    # profile switch can't write ticks into the previous profile's file.
                    def _tick(field: str, url: str):
                        def handler(
                            value: bool, status: dict[str, Any], profile: str
                        ) -> dict[str, Any]:
                            entry = dict(status.get(url, {}))
                            entry[field] = bool(value)
                            entry["updated_at"] = datetime.now(UTC).strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            )
                            updated = {**status, url: entry}
                            save_status(profile, updated)
                            return updated

                        return handler

                    common = dict(
                        inputs=[status_state, profile_state],
                        outputs=[status_state],
                    )
                    reviewed_box.change(
                        _tick("reviewed", job.job_url),
                        inputs=[reviewed_box, *common["inputs"]],
                        outputs=common["outputs"],
                    )
                    applied_box.change(
                        _tick("applied", job.job_url),
                        inputs=[applied_box, *common["inputs"]],
                        outputs=common["outputs"],
                    )

                if shown == 0:
                    gr.Markdown("Everything's been reviewed. Untick *Hide reviewed* to see them.")

        # ---- Events
        def on_load(profile: str):
            profile = (profile or "").strip()
            if not profile:
                return (
                    gr.update(visible=True),
                    gr.update(visible=True, value="Enter a profile name."),
                    gr.update(visible=False),
                    "", [], {}, "",
                )
            try:
                records, status = load_profile(profile)
            except Exception as exc:  # surfaced to the user rather than a blank page
                return (
                    gr.update(visible=True),
                    gr.update(visible=True, value=f"**Couldn't open that profile.** {exc}"),
                    gr.update(visible=False),
                    "", [], {}, "",
                )
            return (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
                profile,
                records,
                status,
                _summary(records, status),
            )

        def on_switch():
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                "", [], {}, "",
            )

        outputs = [
            gate,
            gate_error,
            results_section,
            profile_state,
            jobs_state,
            status_state,
            summary_html,
        ]
        load_btn.click(fn=on_load, inputs=[profile_input], outputs=outputs)
        profile_input.submit(fn=on_load, inputs=[profile_input], outputs=outputs)
        switch_btn.click(fn=on_switch, inputs=None, outputs=outputs)

        # Keep the summary counts honest as boxes are ticked.
        status_state.change(
            fn=_summary, inputs=[jobs_state, status_state], outputs=[summary_html]
        )

    # Gradio 6.0 moved `theme` and `css` from the Blocks constructor to launch().
    # HF Spaces calls demo.launch() itself at boot, so a wrapper is the only place we can
    # inject our theme + CSS without forking the entrypoint. (Same trick as the search Space.)
    _orig_launch = demo.launch

    def _launch_with_theme(*args, **kwargs):
        kwargs.setdefault("theme", theme)
        kwargs.setdefault("css", CSS)
        return _orig_launch(*args, **kwargs)

    demo.launch = _launch_with_theme

    return demo
