from __future__ import annotations

from dataclasses import dataclass

from job_search.config import settings

DATASET_ID = "Divyaamith/Kaggle-Resume"


@dataclass(frozen=True)
class Resume:
    id: int
    category: str
    text: str


def load_resumes(
    sample_size: int | None = None,
    *,
    seed: int | None = None,
    max_chars: int | None = None,
) -> list[Resume]:
    """Load the dataset, clean `Resume_str`, and return a deterministic sample.

    Sampling is stratified-free random with a fixed seed for reproducibility.
    """
    from datasets import load_dataset

    sample_size = sample_size if sample_size is not None else settings.resume_sample_size
    seed = seed if seed is not None else settings.random_seed
    max_chars = max_chars if max_chars is not None else settings.max_resume_chars

    ds = load_dataset(DATASET_ID, split="train")
    ds = ds.shuffle(seed=seed)
    if sample_size is not None:
        ds = ds.select(range(min(sample_size, len(ds))))

    resumes: list[Resume] = []
    for row in ds:
        text = (row["Resume_str"] or "").strip()
        if not text:
            continue
        if len(text) > max_chars:
            text = text[:max_chars]
        resumes.append(
            Resume(id=int(row["ID"]), category=str(row["Category"]).strip(), text=text)
        )
    return resumes
