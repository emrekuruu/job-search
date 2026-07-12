import sys
from pathlib import Path

# HF Spaces' Gradio-SDK Dockerfile installs requirements.txt before copying the workspace,
# so an editable install of `pyproject.toml` isn't possible. Instead, point Python at `src/`
# directly so `from job_search...` resolves.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from job_search.spaces.results.ui import build_app  # noqa: E402

demo = build_app()
demo.queue(default_concurrency_limit=8)

if __name__ == "__main__":
    demo.launch(share=False)
