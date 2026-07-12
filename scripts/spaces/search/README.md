---
title: Job Searcher
emoji: 🎯
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "6.15.2"
app_file: app.py
hardware: zero-gpu
python_version: "3.12"
pinned: false
short_description: Drop your resume. Get matches with reasoning.
tags:
  - llama-cpp
  - gguf
  - lora
  - qwen3
  - distillation
  - resume
  - jobs
models:
  - emrekuruu/job-searcher-qwen3-8B
  - emrekuruu/job-searcher-qwen3-8B-gguf
datasets:
  - emrekuruu/job-search-distill
---

# Job Searcher

Drop your resume. Get matches with the reasoning behind every score.

A Qwen3-8B student distilled from DeepSeek V4 Pro, served via llama.cpp on ZeroGPU.

**Source, dataset card, model cards, and full docs:**
[github.com/emrekuruu/job-search](https://github.com/emrekuruu/job-search)

**Discuss on Reddit:**
[r/huggingface thread](https://www.reddit.com/r/huggingface/comments/1u2qlmk/built_a_small_model_that_reads_your_resume_and/)
