---
title: Job Search Assistant
emoji: 🎯
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "6.15.2"
app_file: app.py
pinned: false
short_description: Upload a resume, get ranked + explained LinkedIn matches
---

# job-search

Distillation pipeline: a **DeepSeek V4** reasoning teacher generates two training datasets
via **PydanticAI**, and a **Qwen/Qwen3-8B** student is distilled (bf16 LoRA SFT) on them and
served with **vLLM** — all training/serving on **Modal**.

Two tasks:
1. **Query generation** — resume → a set of LinkedIn job-search queries.
2. **Fit evaluation** — (resume, job listing) → 5 dimensions × 20 pts (= 100) + reasoning.

## Pipeline

```
resumes ─▶ query_agent ─▶ dataset1.jsonl ─▶ JobSpy ─▶ jobs.jsonl ─▶ eval_agent ─▶ dataset2.jsonl
                                   └────────────── to_sft ──────────────┘
                                                     │
                                  data/sft/*.jsonl ─▶ Modal QLoRA SFT ─▶ LoRA adapters ─▶ vLLM serve
```

## Setup

```bash
uv sync --extra dev
cp .env.example .env   # set DEEPSEEK_API_KEY (+ HF_TOKEN for training)
```

## Generate data (local)

```bash
uv run gen-queries     # Stage 1: dataset1.jsonl
uv run fetch-jobs      # Stage 2: jobs.jsonl   (LinkedIn rate-limits; keep small)
uv run gen-evals       # Stage 3: dataset2.jsonl
uv run to-sft          # data/sft/query_gen.jsonl, data/sft/fit_eval.jsonl
uv run pytest
```

## Train + serve (Modal, GPU)

```bash
modal run modal_apps/train.py --task query_gen
modal run modal_apps/train.py --task fit_eval
modal serve modal_apps/serve.py     # OpenAI-compatible vLLM endpoint -> set VLLM_API_BASE
```

The 5 fit dimensions in `src/job_search/config.py` are placeholders (`TODO: research`); edit and
regenerate `dataset2` + retrain the `fit_eval` adapter when finalized.

## Gradio demo (local)

```bash
uv sync --group space
uv run python app.py        # opens http://localhost:7860
```

## Deploy the Space to HuggingFace

The deploy script ([`scripts/deploy_space.py`](scripts/deploy_space.py)) is idempotent:

```bash
# First time: log in once (writes a cached token)
uv run huggingface-cli login

# Deploy (defaults to the Build-Small-Hackathon org)
uv run python scripts/deploy_space.py

# Useful overrides
uv run python scripts/deploy_space.py --owner <your-user> --name my-fork
uv run python scripts/deploy_space.py --private
uv run python scripts/deploy_space.py --skip-secret    # set DEEPSEEK_API_KEY in Space UI yourself
```

What the script does:
1. `uv export --group space --no-dev` → writes a fresh `requirements.txt` (the workspace project is
   appended as `-e .` so HF's pip install resolves the `src/` layout).
2. Creates the Space (idempotent — re-runs are fine).
3. Pushes `DEEPSEEK_API_KEY` from local `.env` as a Space Secret (skip with `--skip-secret`).
4. Uploads only whitelisted files (`app.py`, `README.md`, `pyproject.toml`, `requirements.txt`,
   `.python-version`, `src/**/*.py`). `data/`, `.env`, `modal_apps/`, caches, etc. stay local.
