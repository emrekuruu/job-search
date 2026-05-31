# Job Search Assistant

Drop a resume, get ranked LinkedIn jobs **with reasoning** — end-to-end on HuggingFace.

[![Build Small Hackathon](https://img.shields.io/badge/Built%20for-Build%20Small%20Hackathon-ff6b6b)](https://huggingface.co/build-small-hackathon)

[![Live Space](https://img.shields.io/badge/🤗%20Space-job--search--assistant-blue)](https://huggingface.co/spaces/emrekuruu/job-search-assistant)

[![Model](https://img.shields.io/badge/🤗%20Model-Qwen3--8B%20LoRA-orange)](https://huggingface.co/emrekuruu/job-searcher-qwen3-8B)

[![Dataset](https://img.shields.io/badge/🤗%20Dataset-job--search--distill-blue)](https://huggingface.co/datasets/emrekuruu/job-search-distill)

[![Built with Gradio](https://img.shields.io/badge/Built%20with-Gradio-orange?logo=gradio)](https://www.gradio.app)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A Qwen3-8B student distilled from **DeepSeek V4 Pro** to do two things from a single resume:
draft LinkedIn job-search queries, and score each returned job's fit on a 5-dimension rubric
with written reasoning. The student runs **in-process via transformers + PEFT** on a
HuggingFace ZeroGPU Space — no external API calls at inference time.

## Live demo

<gradio-app src="https://huggingface.co/spaces/emrekuruu/job-search-assistant"></gradio-app>

## Pipeline

```
resumes ─▶ query_agent ─▶ queries ─▶ JobSpy ─▶ jobs ─▶ eval_agent ─▶ (resume,job,score)
                              └──────────────── teacher labels ───────────────┘
                                                       │
                              SFT splits ─▶ Modal LoRA training ─▶ adapters
                                                       │
                                       HF ZeroGPU Space (transformers + PEFT) ──▶ you
```

## Resources

| | |
|---|---|
| **Live Space** | [emrekuruu/job-search-assistant](https://huggingface.co/spaces/emrekuruu/job-search-assistant) |
| **Dataset** | [emrekuruu/job-search-distill](https://huggingface.co/datasets/emrekuruu/job-search-distill) — four configs: `resume_corpus`, `query_gen_pairings`, `jobs`, `job_evals` |
| **Model (safetensors)** | [emrekuruu/job-searcher-qwen3-8B](https://huggingface.co/emrekuruu/job-searcher-qwen3-8B) — two LoRA adapters on Qwen3-8B (what the live Space loads) |
| **Model (GGUF)** | [emrekuruu/job-searcher-qwen3-8B-gguf](https://huggingface.co/emrekuruu/job-searcher-qwen3-8B-gguf) — base Q4_K_M + LoRA-GGUF adapters, for offline llama.cpp use |
| **Source code** | [github.com/emrekuruu/job-search](https://github.com/emrekuruu/job-search) |

## Dataset

[`emrekuruu/job-search-distill`](https://huggingface.co/datasets/emrekuruu/job-search-distill)
bundles the entire distillation corpus:

- `resume_corpus` — 2.5k resumes, built on [Divyaamith/Kaggle-Resume](https://huggingface.co/datasets/Divyaamith/Kaggle-Resume).
- `query_gen_pairings` — `(resume → reasoning + LinkedIn query set)` from the teacher.
- `jobs` — ~9.9k LinkedIn postings scraped via [JobSpy](https://github.com/Bunsly/JobSpy).
- `job_evals` — `(resume, job) → reasoning + 5-dimension fit score (0–100)`.

Each row carries explicit foreign keys (`resume_id`, `query_id`, `job_id`) so joins are clean.

## Model

A bf16 LoRA fine-tune of [Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B). Two adapters:

- **`query_gen`** — resume → set of LinkedIn search queries.
- **`fit_eval`** — `(resume, job)` → 5 × 20-pt dimension scores + overall reasoning.

Both are published in [safetensors form](https://huggingface.co/emrekuruu/job-searcher-qwen3-8B)
— what the live Space loads via `transformers` + `peft` on ZeroGPU. A
[GGUF mirror](https://huggingface.co/emrekuruu/job-searcher-qwen3-8B-gguf) with a Q4_K_M base
quantization is also available for offline use with `llama-cpp-python`.

## Run locally

```bash
uv sync --group space
uv run python app.py    # opens http://localhost:7860
```

The Space's `app.py` downloads Qwen3-8B + both LoRA adapters from the Hub on first launch
(~16 GB) and runs them in-process via `transformers` + `peft` on the ZeroGPU allocation.

## Reproducing the model

The end-to-end pipeline lives in this repo:

```bash
uv run gen-queries                              # teacher writes search queries (DeepSeek V4 Pro)
uv run fetch-jobs                                # scrape LinkedIn via JobSpy
uv run gen-evals                                 # teacher scores (resume, job) fit
uv run to-sft                                    # → data/sft/{train,val,test}.jsonl
modal run modal_apps/train.py --task query_gen   # LoRA SFT on A100
modal run modal_apps/train.py --task fit_eval --epochs 1
uv run python scripts/deploy_space.py            # push the Space (loads safetensors LoRAs)
```

## Acknowledgments

- **Teacher labels**: [DeepSeek V4 Pro](https://platform.deepseek.com/) via PydanticAI.
- **Resumes**: built on [Divyaamith/Kaggle-Resume](https://huggingface.co/datasets/Divyaamith/Kaggle-Resume) (originally livecareer.com).
- **Jobs**: scraped via [JobSpy](https://github.com/Bunsly/JobSpy).
- **Inference**: [transformers](https://huggingface.co/docs/transformers) + [PEFT](https://huggingface.co/docs/peft).
- **UI + hosting**: [Gradio](https://www.gradio.app) and [HuggingFace ZeroGPU](https://huggingface.co/docs/hub/spaces-zerogpu) for the [Build Small Hackathon](https://huggingface.co/build-small-hackathon).

## License

Apache-2.0. Teacher labels are subject to
[DeepSeek's Open Platform Terms](https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html);
the `jobs` corpus is redistributed public LinkedIn data — downstream users own their compliance.
