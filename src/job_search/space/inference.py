"""Space-side inference using transformers + PEFT on ZeroGPU, with token-streaming.

Critical constraints (learned the hard way):

1. **`.to("cuda")` at module level fails.** ZeroGPU's CUDA emulation covers diffusers'
   `Pipeline.to('cuda')` but NOT `AutoModelForCausalLM.to('cuda')` / `PeftModel.to('cuda')`.
   Load on CPU at root, move to GPU inside the decorated function.

2. **`@spaces.GPU` must be called from the request thread.** Anything that dispatches
   the decorated call to another thread (e.g. `asyncio.to_thread`) breaks the GPU
   context — the worker never gets a real GPU and `.to('cuda')` fails with "Found no
   NVIDIA driver". So the public API exposed here is **sync**: pipeline.py / ui.py
   call these generators directly on the Gradio request thread.

Streaming:

  - The `@spaces.GPU`-decorated generators below run `model.generate(...)` on a
    background `Thread` and pipe its tokens through a `TextIteratorStreamer`.
  - They yield typed events: `{"kind": "token", "text": cumulative}` while the model
    is generating, then a single `{"kind": "done", "result": <Pydantic>, "reasoning":
    <str>}` after the full output lands and the `<think>...</think>` block has been
    split out and the JSON body parsed.
  - Public functions `generate_queries` / `evaluate_fit` are thin pass-throughs
    yielding the same event shape.
"""
from __future__ import annotations

from collections.abc import Iterator
from threading import Thread
from typing import Any

import spaces
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

from job_search.prompts import (
    build_eval_system_prompt,
    build_eval_user,
    build_query_system_prompt,
    build_query_user,
)
from job_search.schemas import FitEvaluation, JobListing, QuerySet

BASE_MODEL = "Qwen/Qwen3-8B"
ADAPTER_REPO = "emrekuruu/job-searcher-qwen3-8B"
MAX_NEW_TOKENS = 4096

# Module-level: load tokenizer + base model + both adapters on CPU.
# `.to("cuda")` is intentionally NOT called here.
_tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
_base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=torch.bfloat16,
    attn_implementation="sdpa",
    low_cpu_mem_usage=True,
)
_model = PeftModel.from_pretrained(
    _base, ADAPTER_REPO, subfolder="query_gen", adapter_name="query_gen"
)
_model.load_adapter(ADAPTER_REPO, subfolder="fit_eval", adapter_name="fit_eval")
_model.eval()


def _split_think(text: str) -> tuple[str, str]:
    """Split the model's output into (reasoning, json_body).

    The student was trained on assistant turns of shape
    `<think>\n{reasoning}\n</think>\n\n{json}` (see `sft_format.py::_assistant`),
    so it emits the same shape at inference. If no <think> block is present we
    return ("", text.strip()).
    """
    text = text.strip()
    if text.startswith("<think>") and "</think>" in text:
        end = text.index("</think>")
        reasoning = text[len("<think>") : end].strip()
        body = text[end + len("</think>") :].strip()
        return reasoning, body
    return "", text


def _stream_generate(
    adapter: str, system: str, user: str, temperature: float,
) -> Iterator[str]:
    """Stream cumulative decoded text from the model. Yields the running join.

    Caller is responsible for adapter selection's lifetime — but `set_adapter` is
    cheap and idempotent, so we just call it here. `_model.to("cuda")` is also
    safe to repeat (no-op after first call).
    """
    _model.to("cuda")
    _model.set_adapter(adapter)
    prompt = _tokenizer.apply_chat_template(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)
    streamer = TextIteratorStreamer(
        _tokenizer, skip_prompt=True, skip_special_tokens=True
    )
    gen_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=True,
        temperature=temperature,
        top_p=0.9,
        pad_token_id=_tokenizer.eos_token_id,
    )
    thread = Thread(target=_model.generate, kwargs=gen_kwargs)
    thread.start()

    parts: list[str] = []
    for chunk in streamer:
        parts.append(chunk)
        yield "".join(parts)
    thread.join()


@spaces.GPU(duration=120)
def _run_query_gen(resume: str, category: str) -> Iterator[dict[str, Any]]:
    full: str = ""
    for cumul in _stream_generate(
        "query_gen",
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


@spaces.GPU(duration=180)
def _run_fit_eval(resume: str, job: JobListing) -> Iterator[dict[str, Any]]:
    full: str = ""
    for cumul in _stream_generate(
        "fit_eval",
        build_eval_system_prompt(),
        build_eval_user(resume, job),
        temperature=0.4,
    ):
        full = cumul
        yield {"kind": "token", "text": cumul}
    reasoning, body = _split_think(full)
    yield {
        "kind": "done",
        "result": FitEvaluation.model_validate_json(body),
        "reasoning": reasoning,
    }


# Public sync streaming API. The `model` kwarg is unused but kept to mirror the
# data-pipeline's agents.py signatures. Each call returns a generator that yields
# {"kind": "token", "text": cumulative} events during generation, then a single
# {"kind": "done", "result": <Pydantic>, "reasoning": <str>} event at the end.
def generate_queries(
    resume: str, category: str, *, model=None,
) -> Iterator[dict[str, Any]]:
    del model
    yield from _run_query_gen(resume, category)


def evaluate_fit(
    resume: str, job: JobListing, *, model=None,
) -> Iterator[dict[str, Any]]:
    del model
    yield from _run_fit_eval(resume, job)
