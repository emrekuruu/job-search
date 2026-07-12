from __future__ import annotations

from pathlib import Path

MIN_CHARS = 200


def extract_resume_text(pdf_path: str | Path) -> str:
    """Pull text out of a (text-native) resume PDF via PyMuPDF.

    Raises a clear `ValueError` if the result is too short to be a real resume — most likely
    an image-only / scanned PDF. We deliberately do NOT silently fall back to vision-OCR;
    the UI surfaces the error and points the user to the textbox.
    """
    import fitz  # PyMuPDF

    pages: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pages.append(page.get_text("text"))

    text = "\n\n".join(p.strip() for p in pages if p.strip())

    if len(text) < MIN_CHARS:
        raise ValueError(
            f"This PDF only yielded {len(text)} characters of text — it appears to be "
            "image-based / scanned. Please paste the resume text into the 'Additional "
            "preferences' box instead."
        )

    return text
