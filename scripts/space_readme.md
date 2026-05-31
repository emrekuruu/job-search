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
  - distillation
  - resume
  - jobs
models:
  - emrekuruu/job-searcher-qwen3-8B
  - emrekuruu/job-searcher-qwen3-8B-gguf
datasets:
  - emrekuruu/job-search-distill
---

# Job Search Assistant

Drop a resume, get ranked LinkedIn jobs with reasoning.

A Qwen3-8B student distilled from DeepSeek V4 Pro, served via llama.cpp on ZeroGPU.

**Source, dataset card, model cards, and full docs:**
[github.com/emrekuruu/job-search](https://github.com/emrekuruu/job-search)
