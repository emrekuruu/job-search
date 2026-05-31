"""Space-side inference using the distilled GGUF model via llama-cpp-python.

Replaces the DeepSeek API call path used by the data-curation pipeline. Loads two
llama.cpp instances — one per LoRA adapter — at module import so each @spaces.GPU
call just runs inference. The distilled student emits structured JSON directly
(constrained by JSON-schema at decode time); there is no `<think>` reasoning trace.
"""
from __future__ import annotations

import asyncio

import spaces
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

from job_search.prompts import (
    build_eval_system_prompt,
    build_eval_user,
    build_query_system_prompt,
    build_query_user,
)
from job_search.schemas import FitEvaluation, JobListing, QuerySet

REPO = "emrekuruu/job-searcher-qwen3-8B-gguf"
N_CTX = 16384
MAX_TOKENS = 4096

# Module-level downloads (cached via hf_hub).
_base_path = hf_hub_download(REPO, "Qwen3-8B-Q4_K_M.gguf")
_query_lora = hf_hub_download(REPO, "query_gen.lora.gguf")
_eval_lora = hf_hub_download(REPO, "fit_eval.lora.gguf")

# Module-level model instantiation. ZeroGPU expects model placement at root level —
# subsequent `@spaces.GPU` calls just invoke inference on these warm instances.
# Two separate Llama instances (one per adapter) is simpler than swapping a single
# instance between scales; the extra ~5 GB VRAM is well within ZeroGPU's 48 GB budget.
_llm_query = Llama(
    model_path=_base_path,
    lora_path=_query_lora,
    n_gpu_layers=-1,
    n_ctx=N_CTX,
    verbose=False,
)
_llm_eval = Llama(
    model_path=_base_path,
    lora_path=_eval_lora,
    n_gpu_layers=-1,
    n_ctx=N_CTX,
    verbose=False,
)


@spaces.GPU(duration=60)
def _run_query_gen(resume: str, category: str) -> QuerySet:
    out = _llm_query.create_chat_completion(
        messages=[
            {"role": "system", "content": build_query_system_prompt()},
            {"role": "user", "content": build_query_user(resume, category)},
        ],
        response_format={
            "type": "json_object",
            "schema": QuerySet.model_json_schema(),
        },
        max_tokens=MAX_TOKENS,
        temperature=0.7,
    )
    return QuerySet.model_validate_json(out["choices"][0]["message"]["content"])


@spaces.GPU(duration=120)
def _run_fit_eval(resume: str, job: JobListing) -> FitEvaluation:
    out = _llm_eval.create_chat_completion(
        messages=[
            {"role": "system", "content": build_eval_system_prompt()},
            {"role": "user", "content": build_eval_user(resume, job)},
        ],
        response_format={
            "type": "json_object",
            "schema": FitEvaluation.model_json_schema(),
        },
        max_tokens=MAX_TOKENS,
        temperature=0.4,
    )
    return FitEvaluation.model_validate_json(out["choices"][0]["message"]["content"])


# Public async API — same signatures as `job_search.agents.generate_queries` and
# `evaluate_fit` so `pipeline.py` only needs an import swap. The unused `model` kwarg
# preserves the call-site shape. Reasoning trace is empty (distilled student emits the
# structured JSON only, no <think> block).
async def generate_queries(
    resume: str, category: str, *, model=None,
) -> tuple[QuerySet, str]:
    del model
    qs = await asyncio.to_thread(_run_query_gen, resume, category)
    return qs, ""


async def evaluate_fit(
    resume: str, job: JobListing, *, model=None,
) -> tuple[FitEvaluation, str]:
    del model
    ev = await asyncio.to_thread(_run_fit_eval, resume, job)
    return ev, ""
