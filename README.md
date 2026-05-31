---
title: Job Search Assistant
emoji: 🎯
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "6.15.2"
app_file: app.py
hardware: zero-gpu
python_version: "3.10"
pinned: false
short_description: Upload a resume, get ranked + explained LinkedIn matches
tags:
  - llama-cpp
  - lora
  - qwen3
models:
  - emrekuruu/job-searcher-qwen3-8B-gguf
---

# job-search

Distillation pipeline: a **DeepSeek V4** reasoning teacher generates two training datasets
via **PydanticAI**, and a **Qwen/Qwen3-8B** student is distilled (bf16 LoRA SFT) on them on
**Modal**, then served via **llama.cpp** on a HuggingFace **ZeroGPU** Space.

Two tasks:
1. **Query generation** — resume → a set of LinkedIn job-search queries.
2. **Fit evaluation** — (resume, job listing) → 5 dimensions × 20 pts (= 100) + reasoning.

## Pipeline

```
resumes ─▶ query_agent ─▶ dataset1.jsonl ─▶ JobSpy ─▶ jobs.jsonl ─▶ eval_agent ─▶ dataset2.jsonl
                                   └────────────── to_sft ──────────────┘
                                                     │
data/sft/*.jsonl ─▶ Modal LoRA SFT ─▶ LoRA adapters ─▶ Modal convert-to-gguf ─▶ HF ZeroGPU Space (llama.cpp)
```

## Setup

```bash
uv sync --extra dev
cp .env.example .env   # set DEEPSEEK_API_KEY
```

## Generate data (local)

```bash
uv run gen-queries     # Stage 1: dataset1.jsonl
uv run fetch-jobs      # Stage 2: jobs.jsonl   (LinkedIn rate-limits; keep small)
uv run gen-evals       # Stage 3: dataset2.jsonl
uv run to-sft          # data/sft/query_gen.jsonl, data/sft/fit_eval.jsonl
uv run pytest
```

## Train + publish GGUFs (Modal, GPU + CPU)

```bash
modal run modal_apps/train.py --task query_gen
modal run modal_apps/train.py --task fit_eval --epochs 1
modal run modal_apps/convert_to_gguf.py     # quantize base + LoRAs -> emrekuruu/job-searcher-qwen3-8B-gguf
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
uv run hf auth login

# Deploy (defaults to emrekuruu/job-search-assistant on ZeroGPU)
uv run python scripts/deploy_space.py

# Useful overrides
uv run python scripts/deploy_space.py --owner <your-user> --name my-fork
uv run python scripts/deploy_space.py --private
```

What the script does:
1. `uv export --group space --no-dev` → writes a fresh `requirements.txt` (the workspace project is
   appended as `-e .` so HF's pip install resolves the `src/` layout).
2. Creates the Space (idempotent — re-runs are fine).
3. Uploads only whitelisted files (`app.py`, `README.md`, `pyproject.toml`, `requirements.txt`,
   `.python-version`, `src/**/*.py`). `data/`, `.env`, `modal_apps/`, caches, etc. stay local.

The Space boots by `hf_hub_download`-ing the three GGUF files from `emrekuruu/job-searcher-qwen3-8B-gguf`,
so make sure `modal run modal_apps/convert_to_gguf.py` has published them before deploying.
