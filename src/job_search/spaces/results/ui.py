"""Results viewer Space: a reader for the daily agent's bucket.

Design rules that keep it alive on a free cpu-basic box:

* **One `gr.HTML` for the list.** A page (20 cards) is a single string; ticks inside the
  cards are plain checkboxes bridged back with `js_on_load` -> `trigger('click', {...})`.
  Never one Gradio component per job again — see `render.py` for the why.
* **All state is per-session `gr.State`.** Records, ticks, page: no module globals, no
  shared mutable dicts across sessions.
* **Every control change funnels through one `view()`.** Filter -> sort -> clamp page ->
  slice -> render. There is exactly one code path that produces what's on screen.
* **Tick writes are serialised** (`concurrency_limit=1`) so two fast clicks can't race the
  whole-file `status.json` upload.
"""
from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gradio as gr

from job_search import store
from job_search.agent.config import ProfileConfig
from job_search.io_utils import read_jsonl
from job_search.preferences import JOB_TYPE_MAP, MODALITY_MAP, none_if_any
from job_search.spaces.results import render as R
from job_search.spaces.results.styles import CSS, JS_ON_LOAD, theme
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


# ---- bucket I/O ----------------------------------------------------------------------------


def load_profile(
    profile: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Fetch one profile's evaluation records, its reviewed/applied ticks, and its config.

    One listing call, then the downloads — the old version listed the folder three times
    per open.
    """
    ps = ProfileStore(_bucket(), profile)
    names = ps.list_names()
    if store.CONFIG not in names:
        raise ValueError(f"No profile named {profile!r} in this bucket.")

    with tempfile.TemporaryDirectory(prefix="job-viewer-") as tmp:
        workdir = Path(tmp)
        config = ps.read_json(store.CONFIG, workdir)
        ProfileConfig.model_validate(config)  # a broken config should fail loudly, here
        records: list[dict[str, Any]] = []
        status: dict[str, Any] = {}
        if store.EVALUATIONS in names:  # absent until the agent's first successful run
            ps.download(store.EVALUATIONS, workdir / store.EVALUATIONS)
            records = list(read_jsonl(workdir / store.EVALUATIONS))
        if store.STATUS in names:
            status = ps.read_json(store.STATUS, workdir)
    return records, status, config


def clear_evaluations(profile: str, stamp: str) -> None:
    ProfileStore(_bucket(), profile).clear_evaluations(stamp)


def save_config(profile: str, config: dict[str, Any]) -> None:
    """Write the profile's config.json. Validated first: the agent reads this file blind
    at 6am, so a bad edit must be rejected here, not discovered in a failed run."""
    ProfileConfig.model_validate(config)
    ProfileStore(_bucket(), profile).write_json(store.CONFIG, config)


# What the Task page edits. The regex screens and search-shape numbers stay config-only.
JOB_TYPE_CHOICES = ["Any", *JOB_TYPE_MAP]
MODALITY_CHOICES = ["Any", *MODALITY_MAP]


def save_status(profile: str, status: dict[str, Any]) -> None:
    """The viewer owns `status.json` outright — the agent never writes it."""
    ProfileStore(_bucket(), profile).write_json(store.STATUS, status)


# ---- the one view function -----------------------------------------------------------------


def view(
    records: list[dict[str, Any]],
    status: dict[str, Any],
    min_score: int,
    hide_reviewed: bool,
    sort: str,
    page: int,
) -> tuple[str, str, int, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """-> (list_html, pager_label, clamped_page, prev/next/clear button updates)."""
    selected = R.select_records(
        records,
        status,
        min_score=min_score,
        hide_reviewed=hide_reviewed,
        sort=sort,
    )
    page = R.clamp_page(int(page), len(selected))
    html = R.render_page(R.page_slice(selected, page), status, has_records=bool(records))
    last = R.page_count(len(selected))
    return (
        html,
        R.page_label(page, len(selected)),
        page,
        gr.update(interactive=page > 1),
        gr.update(interactive=page < last),
        gr.update(interactive=bool(records)),  # nothing to clear on an empty profile
    )


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Your Matches") as demo:
        profile_state = gr.State("")
        records_state = gr.State([])
        status_state = gr.State({})
        config_state = gr.State({})
        page_state = gr.State(1)
        # Whether the "clear all" confirm row is showing. Tracked explicitly because a
        # visible=False sent to an already-hidden row wedges it (see gate_error).
        clear_open = gr.State(False)

        # ---- header
        with gr.Row(elem_id="rv-header"):
            with gr.Column(scale=1):
                gr.Markdown("# Your Matches")
                gr.Markdown(
                    "Every posting your agent found, scored and explained. "
                    "Tick what you've looked at; it's saved to the bucket."
                )
            with gr.Column(scale=0, min_width=220, visible=False) as profile_col:
                profile_chip = gr.HTML()
                switch_btn = gr.Button("Switch profile", size="sm")

        # ---- profile gate
        with gr.Column(visible=True, elem_id="rv-gate") as gate:
            with gr.Group(elem_classes=["rv-gate-card"]):
                profile_input = gr.Textbox(
                    label="Profile",
                    placeholder="e.g. gf-data-analyst",
                    autofocus=True,
                )
                load_btn = gr.Button("Open", variant="primary")
            # Always rendered; empty when there's nothing to say. Toggling `visible` on a
            # component that is already hidden wedges it in Gradio 6.15 (a later
            # visible=True is ignored), so visibility is only ever flipped when it changes.
            gate_error = gr.Markdown("", elem_id="rv-gate-error")

        # ---- results
        with gr.Column(visible=False) as results:
            with gr.Tabs():
                with gr.Tab("Matches"):
                    summary_html = gr.HTML()

                    with gr.Row(elem_id="rv-toolbar"):
                        min_score = gr.Dropdown(
                            choices=R.MIN_SCORE_CHOICES, value=R.DEFAULT_MIN_SCORE,
                            label="Minimum score", scale=1, min_width=140,
                        )
                        sort_by = gr.Dropdown(
                            choices=R.SORT_CHOICES, value=R.SORT_BEST, label="Sort",
                            scale=1, min_width=140,
                        )
                        hide_done = gr.Checkbox(label="Hide reviewed", value=False, scale=0)

                    list_html = gr.HTML(js_on_load=JS_ON_LOAD, elem_id="rv-list")

                    with gr.Row(elem_classes=["rv-pager"]):
                        prev_btn = gr.Button("← Previous", size="sm", scale=0, min_width=120)
                        pager_label = gr.HTML(elem_classes=["rv-pager-label"])
                        next_btn = gr.Button("Next →", size="sm", scale=0, min_width=120)

                    # Clear = archive. Two clicks on purpose; there is no undo button.
                    with gr.Row(elem_id="rv-clear"):
                        clear_btn = gr.Button("Clear all matches…", size="sm", scale=0)
                        with gr.Row(visible=False, scale=1) as clear_confirm:
                            clear_msg = gr.Markdown()
                            clear_yes = gr.Button(
                                "Yes, clear", size="sm", variant="stop", scale=0
                            )
                            clear_no = gr.Button("Cancel", size="sm", scale=0)

                with gr.Tab("Instructions"):
                    gr.Markdown(
                        "What the agent is told about this profile, on top of the resume. "
                        "Two separate notes because two separate models read them. "
                        "Changes apply from the next scheduled run."
                    )
                    with gr.Group(elem_classes=["rv-instr-card"]):
                        gr.Markdown("### Search\nFor the model that writes the LinkedIn queries.")
                        search_instr = gr.Textbox(
                            label="Search instructions",
                            placeholder="Which roles, titles and places to look for; what to avoid searching.",
                            lines=6, max_lines=20, elem_classes=["rv-instr"],
                        )
                        with gr.Row(elem_id="rv-prefs"):
                            category_box = gr.Textbox(label="Role category", scale=2)
                            job_type_dd = gr.Dropdown(
                                choices=JOB_TYPE_CHOICES, label="Job type", scale=1,
                            )
                            modality_dd = gr.Dropdown(
                                choices=MODALITY_CHOICES, label="Modality", scale=1,
                            )
                            location_box = gr.Textbox(label="Location", scale=2)
                    with gr.Group(elem_classes=["rv-instr-card"]):
                        gr.Markdown("### Evaluation\nFor the model that scores each posting against the resume.")
                        eval_instr = gr.Textbox(
                            label="Evaluation instructions",
                            placeholder="Hard disqualifiers, seniority, language, anything a recruiter must know.",
                            lines=14, max_lines=40, elem_classes=["rv-instr"],
                        )
                    with gr.Row():
                        save_task_btn = gr.Button("Save instructions", variant="primary", scale=0)
                        task_msg = gr.Markdown("", elem_id="rv-task-msg")

                with gr.Tab("Queries"):
                    gr.Markdown(
                        "Which searches actually earn their keep. Rate postings with the stars "
                        "on the Matches tab; the average per query shows up here. Weak queries "
                        "are a hint for the search instructions on the Task tab."
                    )
                    queries_html = gr.HTML()

        # ---- wiring
        view_inputs = [records_state, status_state, min_score, hide_done, sort_by, page_state]
        view_outputs = [list_html, pager_label, page_state, prev_btn, next_btn, clear_btn]

        def open_profile(profile: str):
            profile = (profile or "").strip()

            def rejected(message: str):
                # We're at the gate, so gate/results/profile_col are already in the right
                # state — only the message changes.
                return (
                    gr.skip(), message, gr.skip(), gr.skip(),
                    "", [], {}, {}, "", "", "",
                    "", "", "", "Any", "Any", "", "",
                )

            if not profile:
                return rejected("Enter a profile name.")
            try:
                records, status, config = load_profile(profile)
            except Exception as exc:  # surfaced to the user rather than a blank page
                return rejected(f"**Couldn't open that profile.** {exc}")
            return (
                gr.update(visible=False),
                "",
                gr.update(visible=True),
                gr.update(visible=True),
                profile,
                records,
                status,
                config,
                f'<span class="rv-profile-chip">👤 {profile}</span>',
                R.render_summary(records, status),
                R.render_query_stats(records, status),
                config["search_instructions"] or "",
                config["evaluation_instructions"] or "",
                config["category"],
                config["job_type"] or "Any",
                config["modality"] or "Any",
                config["location"] or "",
                "",
            )

        open_outputs = [
            gate, gate_error, results, profile_col,
            profile_state, records_state, status_state, config_state, profile_chip,
            summary_html, queries_html,
            search_instr, eval_instr, category_box, job_type_dd, modality_dd, location_box,
            task_msg,
        ]
        # Load, then render page 1 (chained: `.then` runs with the fresh state values).
        for ev in (load_btn.click, profile_input.submit):
            ev(open_profile, inputs=[profile_input], outputs=open_outputs).then(
                lambda: 1, outputs=[page_state]
            ).then(view, inputs=view_inputs, outputs=view_outputs)

        def close_profile():
            return (
                gr.update(visible=True), "",
                gr.update(visible=False), gr.update(visible=False),
                "", [], {}, {}, "", "", "",
                "", "", "", "Any", "Any", "", "",
            )

        switch_btn.click(close_profile, outputs=open_outputs)

        # Any filter change -> back to page 1 -> re-render.
        for ev in (min_score.change, sort_by.change, hide_done.change):
            ev(lambda: 1, outputs=[page_state]).then(
                view, inputs=view_inputs, outputs=view_outputs
            )

        def go(delta: int):
            def _fn(page: int) -> int:
                return int(page) + delta
            return _fn

        for btn, delta in ((prev_btn, -1), (next_btn, 1)):
            btn.click(go(delta), inputs=[page_state], outputs=[page_state]).then(
                view, inputs=view_inputs, outputs=view_outputs
            ).then(None, js="() => window.scrollTo({top: 0, behavior: 'smooth'})")

        # The Task page: everything else in config.json is carried over untouched.
        def save_task(
            config: dict[str, Any], profile: str,
            search_instructions: str, evaluation_instructions: str,
            category: str, job_type: str, modality: str, location: str,
        ):
            updated = {
                **config,
                "search_instructions": search_instructions.strip() or None,
                "evaluation_instructions": evaluation_instructions.strip() or None,
                "category": category.strip(),
                "job_type": none_if_any(job_type),
                "modality": none_if_any(modality),
                "location": none_if_any(location),
            }
            try:
                save_config(profile, updated)
            except Exception as exc:
                return config, f"**Not saved.** {exc}"
            stamp = datetime.now(UTC).strftime("%H:%M UTC")
            return updated, f"Saved at {stamp}. The next scheduled run will use it."

        save_task_btn.click(
            save_task,
            inputs=[
                config_state, profile_state,
                search_instr, eval_instr, category_box, job_type_dd, modality_dd, location_box,
            ],
            outputs=[config_state, task_msg],
            concurrency_limit=1,
        )

        # Clear all: archive in the bucket, then reload the (now empty) profile.
        def hide_confirm(is_open: bool):
            return (gr.update(visible=False) if is_open else gr.skip()), False

        def ask_clear(records: list, is_open: bool):
            n = len(records)
            return (
                gr.skip() if is_open else gr.update(visible=True),
                True,
                f"Archive all **{n}** evaluations for this profile? They leave this "
                "list for good (the agent still remembers them, so they won't come back). "
                "Don't do this while the daily run is in progress.",
            )

        def do_clear(profile: str):
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            try:
                clear_evaluations(profile, stamp)
            except Exception as exc:
                return gr.skip(), gr.skip(), gr.skip(), gr.skip(), f"**Couldn't clear.** {exc}", False
            return [], {}, R.render_summary([], {}), R.render_query_stats([], {}), "", True

        clear_btn.click(
            ask_clear, inputs=[records_state, clear_open],
            outputs=[clear_confirm, clear_open, clear_msg],
        )
        clear_no.click(hide_confirm, inputs=[clear_open], outputs=[clear_confirm, clear_open])
        cleared_ok = gr.State(False)
        clear_yes.click(
            do_clear,
            inputs=[profile_state],
            outputs=[records_state, status_state, summary_html, queries_html, clear_msg, cleared_ok],
            concurrency_limit=1,
        ).then(lambda: 1, outputs=[page_state]).then(
            view, inputs=view_inputs, outputs=view_outputs
        ).then(
            lambda ok, is_open: hide_confirm(is_open) if ok else (gr.skip(), is_open),
            inputs=[cleared_ok, clear_open], outputs=[clear_confirm, clear_open],
        )
        switch_btn.click(hide_confirm, inputs=[clear_open], outputs=[clear_confirm, clear_open])

        # A tick inside a card: persist, then refresh the counters. The list is NOT
        # re-rendered — the checkbox already reflects the new state on the client.
        def tick(status: dict[str, Any], profile: str, records: list, evt: gr.EventData):
            entry = dict(status.get(evt.url, {}))
            if evt.field == "rating":
                value = int(evt.value)
                if not 1 <= value <= R.MAX_RATING:
                    raise ValueError(f"rating {value} out of range 1..{R.MAX_RATING}")
                entry["rating"] = value
            elif evt.field in ("reviewed", "applied"):
                entry[evt.field] = bool(evt.value)
            else:
                raise ValueError(f"unknown status field {evt.field!r}")
            entry["updated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            updated = {**status, evt.url: entry}
            save_status(profile, updated)
            return updated, R.render_summary(records, updated), R.render_query_stats(records, updated)

        list_html.click(
            tick,
            inputs=[status_state, profile_state, records_state],
            outputs=[status_state, summary_html, queries_html],
            concurrency_limit=1,
        )

    # Gradio 6 takes `theme` / `css` on launch(), which HF Spaces calls itself.
    _orig_launch = demo.launch

    def _launch_with_theme(*args, **kwargs):
        kwargs.setdefault("theme", theme)
        kwargs.setdefault("css", CSS)
        return _orig_launch(*args, **kwargs)

    demo.launch = _launch_with_theme
    return demo
