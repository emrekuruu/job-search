"""Space-side inference.

Backend is chosen at module import based on whether we're inside HF Spaces:

  * **On HF Spaces** (the `SPACE_ID` env var is set by HF): use the distilled student —
    Qwen3-8B Q4_K_M GGUF + per-task LoRA-GGUF adapters via **llama-cpp-python**
    running locally in-process under ZeroGPU. Token-by-token streaming via the
    OpenAI-style `stream=True` chat-completion API.

  * **Locally** (no `SPACE_ID`): use **DeepSeek V4 Pro** via PydanticAI. The local
    dev machine doesn't need 16 GB of CUDA RAM, and DeepSeek is much faster than
    CPU inference (also identical quality — it's literally the teacher). No
    token streaming (PydanticAI's `agent.run_sync` is one-shot), but the per-stage
    UI updates from `pipeline.py` still drive the streaming feel.

Both paths expose the same generator-yielding API so `pipeline.py` doesn't care.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

from job_search.schemas import FitEvaluation, JobListing, QuerySet

_ON_SPACE = bool(os.environ.get("SPACE_ID"))


if _ON_SPACE:
    # =================================================================================
    # HF Space backend: Qwen3-8B Q4_K_M GGUF + LoRA adapters via llama-cpp-python on
    # ZeroGPU. The Llama instance is constructed INSIDE @spaces.GPU because ZeroGPU
    # recycles the CUDA context per decorated call — a module-level instance would
    # hold a dead context on the second use.
    # =================================================================================
    import spaces
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    from job_search.prompts import (
        build_eval_system_prompt,
        build_eval_user,
        build_query_system_prompt,
        build_query_user,
    )

    GGUF_REPO = "emrekuruu/job-searcher-qwen3-8B-gguf"
    BASE_GGUF = "Qwen3-8B-Q4_K_M.gguf"
    QUERY_LORA_GGUF = "query_gen.lora.gguf"
    EVAL_LORA_GGUF = "fit_eval.lora.gguf"
    # fit_eval's <think> trace (1500-3000 tok) + structured JSON (500-1500 tok)
    # easily exceeds 2048. With duration=1500s on @spaces.GPU we have plenty of
    # time budget, so size for the verbose case.
    MAX_NEW_TOKENS = 8192
    N_CTX = 8192

    # Pull the GGUF artifacts to the HF cache at import time (cold-start only).
    # hf_hub_download is just disk/network — no GPU context needed, so it must
    # NOT live inside @spaces.GPU.
    _BASE_PATH = hf_hub_download(GGUF_REPO, BASE_GGUF)
    _QUERY_LORA_PATH = hf_hub_download(GGUF_REPO, QUERY_LORA_GGUF)
    _EVAL_LORA_PATH = hf_hub_download(GGUF_REPO, EVAL_LORA_GGUF)

    def _split_think(text: str) -> tuple[str, str]:
        """Split <think>...</think>\\n\\n{json} into (reasoning, json_body)."""
        text = text.strip()
        if text.startswith("<think>") and "</think>" in text:
            end = text.index("</think>")
            reasoning = text[len("<think>") : end].strip()
            body = text[end + len("</think>") :].strip()
            return reasoning, body
        return "", text

    def _stream_chat(
        llm: Llama, system: str, user: str, temperature: float,
    ) -> Iterator[str]:
        """Yield cumulative decoded text from llama-cpp's streaming chat completion."""
        completion = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            top_p=0.9,
            max_tokens=MAX_NEW_TOKENS,
            stream=True,
        )
        parts: list[str] = []
        for chunk in completion:
            delta = chunk["choices"][0]["delta"].get("content")
            if delta:
                parts.append(delta)
                yield "".join(parts)

    @spaces.GPU(duration=1800)
    def _run_query_gen(resume: str, category: str) -> Iterator[dict[str, Any]]:
        llm = Llama(
            model_path=_BASE_PATH,
            lora_path=_QUERY_LORA_PATH,
            n_gpu_layers=-1,
            n_ctx=N_CTX,
            flash_attn=True,
            verbose=False,
        )
        full = ""
        for cumul in _stream_chat(
            llm,
            build_query_system_prompt(),
            build_query_user(resume, category),
            temperature=0.7,
        ):
            full = cumul
            yield {"kind": "token", "text": cumul}
        reasoning, body = _split_think(full)
        yield {
            "kind": "done",
            "result": QuerySet.model_validate_json(body),
            "reasoning": reasoning,
        }

    @spaces.GPU(duration=1800)
    def _run_fit_eval_batch(
        resume: str, jobs: list[JobListing],
    ) -> Iterator[dict[str, Any]]:
        """All jobs evaluated inside ONE @spaces.GPU call.

        Why batched: each @spaces.GPU call acquires a fresh ZeroGPU proxy token,
        and the token has a much shorter lifetime than the `duration=` budget
        (empirically ~2-3 min). With N separate per-job calls we burn a token
        per job, and the second token request comes back expired right after
        the first fit_eval finishes. Loading Llama once and yielding per-job
        events keeps us inside a single token's life, and as a bonus pays the
        model-load cold-start once instead of N times.
        """
        llm = Llama(
            model_path=_BASE_PATH,
            lora_path=_EVAL_LORA_PATH,
            n_gpu_layers=-1,
            n_ctx=N_CTX,
            flash_attn=True,
            verbose=False,
        )
        for job in jobs:
            full = ""
            for cumul in _stream_chat(
                llm,
                build_eval_system_prompt(),
                build_eval_user(resume, job),
                temperature=0.4,
            ):
                full = cumul
                yield {"kind": "token", "job": job, "text": cumul}
            reasoning, body = _split_think(full)
            yield {
                "kind": "done",
                "job": job,
                "result": FitEvaluation.model_validate_json(body),
                "reasoning": reasoning,
            }

    def generate_queries(
        resume: str, category: str, *, model=None,
    ) -> Iterator[dict[str, Any]]:
        del model
        yield from _run_query_gen(resume, category)

    def evaluate_fit_batch(
        resume: str, jobs: list[JobListing], *, model=None,
    ) -> Iterator[dict[str, Any]]:
        del model
        yield from _run_fit_eval_batch(resume, jobs)

else:
    # =================================================================================
    # Local dev backend: DeepSeek V4 Pro via PydanticAI. One-shot (no streaming).
    # =================================================================================
    import asyncio

    from job_search.agents import evaluate_fit as _ds_evaluate_fit
    from job_search.agents import generate_queries as _ds_generate_queries
    from job_search.providers import get_model

    _ds_model = None

    def _get_ds_model():
        global _ds_model
        if _ds_model is None:
            _ds_model = get_model("deepseek")
        return _ds_model

    def generate_queries(
        resume: str, category: str, *, model=None,
    ) -> Iterator[dict[str, Any]]:
        del model
        queryset, reasoning = asyncio.run(
            _ds_generate_queries(resume, category, model=_get_ds_model())
        )
        yield {"kind": "done", "result": queryset, "reasoning": reasoning}

    def evaluate_fit_batch(
        resume: str, jobs: list[JobListing], *, model=None,
    ) -> Iterator[dict[str, Any]]:
        del model
        ds_model = _get_ds_model()
        for job in jobs:
            evaluation, reasoning = asyncio.run(
                _ds_evaluate_fit(resume, job, model=ds_model)
            )
            yield {
                "kind": "done",
                "job": job,
                "result": evaluation,
                "reasoning": reasoning,
            }
