from __future__ import annotations

import gradio as gr

from job_search.spaces.common.cards import (
    render_job_card,
    render_query_card,
    render_streaming_eval_card,
)
from job_search.spaces.common.theme import CSS, theme
from job_search.spaces.search.ocr import extract_resume_text
from job_search.spaces.search.pipeline import stream_pipeline

JOB_TYPE_CHOICES = ["Any", "Full-time", "Part-time", "Contract", "Internship"]
MODALITY_CHOICES = ["Any", "Remote", "Hybrid", "On-premise"]

_PENDING = "pending"
_BUSY = "busy"
_DONE = "done"

EMPTY_QUERIES_HTML = "<em>Submit a resume to generate LinkedIn search queries.</em>"
EMPTY_RANKED_HTML = "<em>Ranked job matches will stream in here as they are scored.</em>"


def _stepper(
    resume: str = _PENDING,
    queries: str = _PENDING,
    search: str = _PENDING,
    evaluate: str = _PENDING,
    *,
    search_count: int | None = None,
    eval_count: tuple[int, int] | None = None,
    done_count: int | None = None,
) -> str:
    """4-step horizontal progress with circles + connector lines + detail captions."""

    def _icon(state: str, step_number: int) -> str:
        return {"pending": str(step_number), "busy": "•", "done": "✓"}[state]

    def _step(label: str, state: str, detail: str, step_number: int) -> str:
        return (
            f'<div class="step {state}">'
            f'  <div class="step-circle">{_icon(state, step_number)}</div>'
            f'  <div class="step-label">{label}</div>'
            f'  <div class="step-detail">{detail}</div>'
            f"</div>"
        )

    s_detail = f"{search_count} jobs" if search_count is not None else ""
    if done_count is not None:
        e_detail = f"🎉 {done_count} scored"
    elif eval_count is not None:
        e_detail = f"{eval_count[0]}/{eval_count[1]} scored"
    else:
        e_detail = ""

    return (
        '<div class="stepper">'
        + _step("Resume", resume, "", 1)
        + _step("Queries", queries, "", 2)
        + _step("Search", search, s_detail, 3)
        + _step("Evaluate", evaluate, e_detail, 4)
        + "</div>"
    )


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Job Searcher") as demo:
        # ---- Decorative aurora background (sits behind everything, pointer-events: none)
        gr.HTML(
            '<div id="aurora-bg">'
            '  <div class="aurora-blob aurora-1"></div>'
            '  <div class="aurora-blob aurora-2"></div>'
            '  <div class="aurora-blob aurora-3"></div>'
            "</div>"
        )

        # ---- Hero
        with gr.Column(elem_id="hero"):
            gr.Markdown("# Job Searcher")
            gr.Markdown(
                "Drop your resume. Get matches with the reasoning behind every score."
            )

        # ---- Inputs section (hidden once streaming starts; brought back via Start over)
        with gr.Column(visible=True, elem_classes=["inputs-section"]) as inputs_section:
            with gr.Row(equal_height=True):
                with gr.Column(scale=1, elem_classes=["upload-column"]):
                    gr.HTML('<div class="section-label">Resume</div>')
                    pdf_input = gr.File(
                        file_types=[".pdf"],
                        show_label=False,
                        type="filepath",
                        height=300,
                        elem_classes=["upload-zone"],
                    )

                with gr.Column(scale=2):
                    with gr.Group(elem_classes=["glass-panel"]):
                        with gr.Column(elem_classes=["preference-section"]):
                            gr.HTML('<div class="section-label">Job type</div>')
                            job_type_input = gr.Radio(
                                choices=JOB_TYPE_CHOICES,
                                value="Any",
                                show_label=False,
                                elem_classes=["preference-radio"],
                            )

                        gr.HTML('<div class="section-divider"></div>')

                        with gr.Column(elem_classes=["preference-section"]):
                            gr.HTML('<div class="section-label">Work modality</div>')
                            modality_input = gr.Radio(
                                choices=MODALITY_CHOICES,
                                value="Any",
                                show_label=False,
                                elem_classes=["preference-radio"],
                            )

                        gr.HTML('<div class="section-divider"></div>')

                        with gr.Column(elem_classes=["preference-section"]):
                            gr.HTML('<div class="section-label">Location</div>')
                            location_input = gr.Textbox(
                                show_label=False,
                                placeholder="San Francisco · London · Remote · anywhere",
                            )

                        gr.HTML('<div class="section-divider"></div>')

                        with gr.Column(elem_classes=["preference-section"]):
                            gr.HTML('<div class="section-label">Anything else</div>')
                            extra_input = gr.Textbox(
                                show_label=False,
                                lines=1,
                                max_lines=4,  # grows as the user types, starts compact
                                placeholder=(
                                    "e.g. 'minimum $150k base · open to startups'"
                                ),
                            )

            with gr.Row(elem_classes=["submit-row"]):
                submit_btn = gr.Button(
                    "Find my matches",
                    variant="primary",
                    size="lg",
                    elem_classes=["submit-cta"],
                )

        # ---- Start-over (only visible after submission)
        with gr.Row(elem_classes=["start-over-row"]):
            start_over_btn = gr.Button(
                "← Start over",
                variant="secondary",
                size="sm",
                visible=False,
                scale=0,
            )

        # ---- Results section (hidden until submission; revealed once streaming starts)
        with gr.Column(visible=False, elem_classes=["results-section"]) as results_section:
            progress_html = gr.HTML(_stepper())

            with gr.Tabs(elem_classes=["main-tabs"]):
                with gr.Tab("Search queries"):
                    queries_html = gr.HTML(EMPTY_QUERIES_HTML)
                    with gr.Accordion(
                        "Why these queries — model reasoning",
                        open=True,
                        elem_classes=["reasoning-accordion"],
                    ):
                        queries_reasoning_md = gr.Markdown(
                            "",
                            elem_classes=["reasoning-content"],
                        )
                with gr.Tab("Ranked matches"):
                    ranked_html = gr.HTML(EMPTY_RANKED_HTML)

        # ---- Submit handler
        def on_submit(
            pdf_path: str | None,
            job_type: str,
            modality: str,
            location: str,
            extra: str,
        ):
            if not pdf_path:
                raise gr.Error("Please upload a resume PDF.")
            try:
                resume_text = extract_resume_text(pdf_path)
            except ValueError as e:
                raise gr.Error(str(e)) from e

            # Resume parsed → hide inputs, reveal Start-over + results section, kick off queries.
            yield (
                gr.update(visible=False),   # inputs_section
                gr.update(visible=True),    # start_over_btn
                gr.update(visible=True),    # results_section
                _stepper(resume=_DONE, queries=_BUSY),
                "",
                "",
                "<em>Working…</em>",
            )

            cards_by_url: dict[str, tuple[int, str]] = {}
            total_jobs = 0
            total_evals = 0

            for event in stream_pipeline(
                resume_text,
                extra,
                job_type=job_type,
                modality=modality,
                location=location,
            ):
                kind = event["kind"]

                if kind == "query_token":
                    # Live reasoning streaming into the accordion under the queries tab.
                    yield (
                        gr.update(),
                        gr.update(),
                        gr.update(),
                        _stepper(resume=_DONE, queries=_BUSY),
                        gr.update(),
                        event["reasoning"],
                        gr.update(),
                    )

                elif kind == "eval_token":
                    # Streaming reasoning for one (resume, job) pair. Placeholder card
                    # at a high pseudo-score so the in-progress card pins to the top of
                    # the ranked list; the final `evaluation` event overwrites it with
                    # the real card + real total, and it re-sorts naturally.
                    job = event["job"]
                    cards_by_url[job.job_url] = (
                        200,
                        render_streaming_eval_card(job, event["reasoning"]),
                    )
                    sorted_cards = "".join(
                        h for _, h in sorted(
                            cards_by_url.values(), key=lambda kv: kv[0], reverse=True
                        )
                    )
                    yield (
                        gr.update(),
                        gr.update(),
                        gr.update(),
                        _stepper(
                            resume=_DONE, queries=_DONE, search=_DONE, evaluate=_BUSY,
                            search_count=total_jobs,
                            eval_count=(total_evals, total_jobs),
                        ),
                        gr.update(),
                        gr.update(),
                        sorted_cards,
                    )

                elif kind == "queries":
                    queries_html_str = "".join(
                        render_query_card(q) for q in event["queries"]
                    )
                    yield (
                        gr.update(),
                        gr.update(),
                        gr.update(),
                        _stepper(resume=_DONE, queries=_DONE, search=_BUSY),
                        queries_html_str,
                        event["reasoning"],
                        gr.update(),
                    )

                elif kind == "jobs_after_query":
                    total_jobs = event["total"]
                    yield (
                        gr.update(),
                        gr.update(),
                        gr.update(),
                        _stepper(
                            resume=_DONE, queries=_DONE, search=_BUSY,
                            search_count=total_jobs,
                        ),
                        gr.update(),
                        gr.update(),
                        gr.update(),
                    )

                elif kind == "evaluation":
                    job = event["job"]
                    ev = event["evaluation"]
                    cards_by_url[job.job_url] = (ev.total, render_job_card(job, ev))
                    total_evals += 1
                    sorted_cards = "".join(
                        html
                        for _, html in sorted(
                            cards_by_url.values(), key=lambda kv: kv[0], reverse=True
                        )
                    )
                    yield (
                        gr.update(),
                        gr.update(),
                        gr.update(),
                        _stepper(
                            resume=_DONE, queries=_DONE, search=_DONE, evaluate=_BUSY,
                            search_count=total_jobs,
                            eval_count=(total_evals, total_jobs),
                        ),
                        gr.update(),
                        gr.update(),
                        sorted_cards,
                    )

                elif kind == "done":
                    n = len(event["ranked"])
                    yield (
                        gr.update(),
                        gr.update(),
                        gr.update(),
                        _stepper(
                            resume=_DONE, queries=_DONE, search=_DONE, evaluate=_DONE,
                            search_count=total_jobs,
                            done_count=n,
                        ),
                        gr.update(),
                        gr.update(),
                        gr.update(),
                    )

        # ---- Start-over handler: bring inputs back + hide+clear results.
        def on_start_over():
            return (
                gr.update(visible=True),     # inputs_section
                gr.update(visible=False),    # start_over_btn
                gr.update(visible=False),    # results_section
                _stepper(),                  # progress reset
                EMPTY_QUERIES_HTML,
                "",
                EMPTY_RANKED_HTML,
            )

        # Shared output list for both handlers — order matters.
        outputs = [
            inputs_section,
            start_over_btn,
            results_section,
            progress_html,
            queries_html,
            queries_reasoning_md,
            ranked_html,
        ]

        submit_btn.click(
            fn=on_submit,
            inputs=[
                pdf_input,
                job_type_input,
                modality_input,
                location_input,
                extra_input,
            ],
            outputs=outputs,
        )
        start_over_btn.click(fn=on_start_over, inputs=None, outputs=outputs)

    # Gradio 6.0 moved `theme` and `css` from the Blocks constructor to launch().
    # HF Spaces calls demo.launch() itself at boot, so a sys-time wrapper is the
    # only place we can inject our theme + CSS without forking the entrypoint.
    _orig_launch = demo.launch

    def _launch_with_theme(*args, **kwargs):
        kwargs.setdefault("theme", theme)
        kwargs.setdefault("css", CSS)
        return _orig_launch(*args, **kwargs)

    demo.launch = _launch_with_theme

    return demo
