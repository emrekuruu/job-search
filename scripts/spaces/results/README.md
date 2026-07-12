---
title: Your Matches
emoji: 📋
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "6.15.2"
app_file: app_results.py
python_version: "3.12"
pinned: false
short_description: Ranked job matches from your daily agent, with reasoning.
tags:
  - jobs
  - resume
  - agent
---

# Your Matches

A reader for the job-search agent's bucket.

Every night a scheduled [Hugging Face Job](https://huggingface.co/docs/hub/jobs-overview)
searches LinkedIn for a **profile** — a role track like `gf-data-analyst`, each with its own
resume and preferences — skips every posting it has already scored, evaluates the newest 25
against the resume across five weighted dimensions, and appends the results to a Storage
Bucket.

This Space renders them: open a profile, see the matches ranked best-first with the full
reasoning behind every score, and tick **Reviewed** / **Applied** as you work through them.
The ticks are saved back to the bucket, so they survive a refresh and show up in the Excel
report the agent regenerates each run.

The scoring model is the distilled student from
[job-searcher-qwen3-8B](https://huggingface.co/emrekuruu/job-searcher-qwen3-8B) — try it
interactively on the [Job Searcher](https://huggingface.co/spaces/emrekuruu/job-search-assistant)
Space.
