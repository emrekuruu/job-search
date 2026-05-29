# job-search

Distillation pipeline: a **DeepSeek V4** reasoning teacher generates two training datasets
via **PydanticAI**, and a **Qwen/Qwen3.5-9B** student is distilled (QLoRA SFT) on them and
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
