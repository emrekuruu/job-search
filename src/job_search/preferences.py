from __future__ import annotations

# UI labels -> JobSpy-compatible values. "Any" is treated as no preference.
JOB_TYPE_MAP: dict[str, str] = {
    "Full-time": "fulltime",
    "Part-time": "parttime",
    "Contract": "contract",
    "Internship": "internship",
}

# Modality is a soft signal — `Remote` translates to `is_remote=True` on the JobQuery side via the
# LLM; Hybrid / On-premise stay as text so the LLM can embed them in the search term.
MODALITY_MAP: dict[str, str] = {
    "Remote": "remote",
    "Hybrid": "hybrid",
    "On-premise": "on-premise",
}


def none_if_any(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if not v or v.lower() == "any":
        return None
    return v


def build_input(
    resume_text: str,
    extra: str | None,
    job_type: str | None,
    modality: str | None,
    location: str | None,
) -> str:
    """Pack the resume + structured preferences into one input the agent will see.

    Shared by the interactive Space (`spaces/search/pipeline.py`) and the headless daily
    agent (`agent/run.py`) so the two cannot drift apart in how they present preferences
    to the model.
    """
    job_type_norm = JOB_TYPE_MAP.get(job_type or "", job_type) if job_type else None
    modality_norm = MODALITY_MAP.get(modality or "", modality) if modality else None

    lines: list[str] = []
    if job_type_norm:
        lines.append(f"- Job type: {job_type_norm}")
    if modality_norm:
        lines.append(f"- Work modality: {modality_norm}")
    if location:
        lines.append(f"- Location: {location}")
    if extra and extra.strip():
        lines.append(f"- Free-form notes: {extra.strip()}")

    if not lines:
        return resume_text
    return f"{resume_text}\n\nExplicit preferences from candidate (use these in every query):\n" + "\n".join(lines)
