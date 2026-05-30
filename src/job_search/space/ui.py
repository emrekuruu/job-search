from __future__ import annotations

import gradio as gr

from job_search.space.cards import render_job_card, render_query_card
from job_search.space.ocr import extract_resume_text
from job_search.space.pipeline import stream_pipeline
from job_search.space.theme import CSS, theme

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
    with gr.Blocks(theme=theme, css=CSS, title="Job Search Assistant") as demo:
        # ---- Hero
        with gr.Column(elem_id="hero"):
            gr.Markdown("# Job Search Assistant")
            gr.Markdown(
                "Upload your resume — DeepSeek V4 Pro generates targeted LinkedIn queries, "
                "we surface matching jobs, then score each one on five dimensions with reasoning."
            )

        # ---- Inputs section (hidden once streaming starts; brought back via Start over)
        with gr.Column(visible=True) as inputs_section:
            with gr.Row():
                with gr.Column(scale=1):
                    pdf_input = gr.File(
                        file_types=[".pdf"],
                        label="📄 Resume PDF",
                        type="filepath",
                        height=240,
                        elem_classes=["upload-zone"],
                    )

                with gr.Column(scale=2):
                    with gr.Group(elem_classes=["glass-panel"]):
                        gr.Markdown("### 🎯 What kind of job are you looking for?")
                        with gr.Row():
                            job_type_input = gr.Radio(
                                choices=JOB_TYPE_CHOICES,
                                value="Any",
                                label="Job type",
                                elem_classes=["preference-radio"],
                            )
                            modality_input = gr.Radio(
                                choices=MODALITY_CHOICES,
                                value="Any",
                                label="Work modality",
                                elem_classes=["preference-radio"],
                            )
                        location_input = gr.Textbox(
                            label="Location",
                            placeholder="e.g. 'San Francisco, CA' or 'EU' (leave blank for anywhere)",
                        )
                        extra_input = gr.Textbox(
                            label="Anything else? (optional)",
                            lines=4,
                            placeholder=(
                                "e.g. 'minimum $150k base; open to startups; happy to relocate "
                                "for the right team'"
                            ),
                        )

            submit_btn = gr.Button("🚀 Find My Jobs", variant="primary", size="lg")

        # ---- Start-over (only visible after submission)
        with gr.Row(elem_classes=["start-over-row"]):
            start_over_btn = gr.Button(
                "← Start over",
                variant="secondary",
                size="sm",
                visible=False,
                scale=0,
            )

        # ---- Progress + results
        progress_html = gr.HTML(_stepper())

        with gr.Tabs():
            with gr.Tab("🔍 Search Queries"):
                queries_html = gr.HTML(EMPTY_QUERIES_HTML)
                with gr.Accordion("Model reasoning", open=False):
                    queries_reasoning_md = gr.Markdown("")
            with gr.Tab("🎯 Ranked Matches"):
                ranked_html = gr.HTML(EMPTY_RANKED_HTML)

        # ---- Submit handler
        async def on_submit(
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

            # Resume parsed → hide inputs, reveal Start-over, kick off queries.
            yield (
                gr.update(visible=False),   # inputs_section
                gr.update(visible=True),    # start_over_btn
                _stepper(resume=_DONE, queries=_BUSY),
                "",
                "",
                "<em>Working…</em>",
            )

            cards_by_url: dict[str, tuple[int, str]] = {}
            total_jobs = 0
            total_evals = 0

            async for event in stream_pipeline(
                resume_text,
                extra,
                job_type=job_type,
                modality=modality,
                location=location,
            ):
                kind = event["kind"]

                if kind == "queries":
                    queries_html_str = "".join(
                        render_query_card(q) for q in event["queries"]
                    )
                    yield (
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
                        _stepper(
                            resume=_DONE, queries=_DONE, search=_DONE, evaluate=_DONE,
                            search_count=total_jobs,
                            done_count=n,
                        ),
                        gr.update(),
                        gr.update(),
                        gr.update(),
                    )

        # ---- Start-over handler: bring inputs back + clear results.
        def on_start_over():
            return (
                gr.update(visible=True),     # inputs_section
                gr.update(visible=False),    # start_over_btn
                _stepper(),                  # progress reset
                EMPTY_QUERIES_HTML,
                "",
                EMPTY_RANKED_HTML,
            )

        # Shared output list for both handlers — order matters.
        outputs = [
            inputs_section,
            start_over_btn,
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

    return demo
