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

This Space renders them, 20 to a page, best match first and 50+ by default:

- **Matches** — every posting with the full reasoning behind its score. Rate each one out
  of 10 stars and tick **Applied**. Everything is saved back to the bucket, so
  it survives a refresh and shows up in the Excel report the agent regenerates each run.
  **Clear all matches** archives the whole list to `archive/<timestamp>/` when it gets too
  long — the agent still remembers them, so they won't be re-scraped.
- **Task** — the two notes the agent gets on top of the resume: *search instructions* for the
  model that writes the LinkedIn queries, *evaluation instructions* for the model that scores
  each posting (hard disqualifiers, seniority, language). Edit and save; the next run uses it.
- **Queries** — which searches surfaced which postings, with the model's average score and
  your average star rating per query, so weak queries are easy to spot and cut.

The scoring model is the distilled student from
[job-searcher-qwen3-8B](https://huggingface.co/emrekuruu/job-searcher-qwen3-8B) — try it
interactively on the [Job Searcher](https://huggingface.co/spaces/emrekuruu/job-search-assistant)
Space.
