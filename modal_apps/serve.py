from __future__ import annotations

import modal

BASE_MODEL = "Qwen/Qwen3-8B"
VLLM_PORT = 8000

# Image deps live in pyproject.toml's `[dependency-groups].serve`.
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_sync(uv_project_dir="./", groups=["serve"], gpu="A100")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

app = modal.App("job-search-serve")
adapters_vol = modal.Volume.from_name("job-search-adapters", create_if_missing=True)
hf_cache_vol = modal.Volume.from_name("job-search-hf-cache", create_if_missing=True)


@app.function(
    image=image,
    gpu="A100-40GB",
    timeout=60 * 60,
    scaledown_window=15 * 60,
    volumes={"/adapters": adapters_vol, "/root/.cache/huggingface": hf_cache_vol},
    secrets=[modal.Secret.from_name("huggingface")],
)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * 60)
def serve() -> None:
    import subprocess

    cmd = [
        "vllm",
        "serve",
        BASE_MODEL,
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
        "--enable-lora",
        "--max-lora-rank", "16",
        "--lora-modules",
        "query_gen=/adapters/query_gen",
        "fit_eval=/adapters/fit_eval",
    ]
    subprocess.Popen(" ".join(cmd), shell=True)
