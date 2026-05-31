"""Deploy the Gradio app to a HuggingFace Space.

The project README at the repo root is the **GitHub-facing** project page (no YAML
frontmatter). The Space's README, with `hardware: zero-gpu` and friends, lives at
`scripts/space_readme.md` and is uploaded separately as `README.md` on the Space.

Run:
  uv run python scripts/deploy_space.py
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from huggingface_hub import HfApi
except ImportError:
    sys.exit(
        "huggingface_hub is not installed. Run `uv sync` (it's in the dev group) and re-try."
    )

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OWNER = "emrekuruu"
DEFAULT_NAME = "job-search-assistant"

# Code + config files shipped to the Space. The Space's README is uploaded separately from
# `scripts/space_readme.md` — the root README.md is the GitHub-facing project README.
ALLOW_PATTERNS = [
    "app.py",
    "pyproject.toml",
    "requirements.txt",
    ".python-version",
    "src/**/*.py",
]
IGNORE_PATTERNS = [
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.ruff_cache/**",
]
SPACE_README_SRC = PROJECT_ROOT / "scripts" / "space_readme.md"


def generate_requirements() -> Path:
    """Export the locked `space` group deps to requirements.txt for HF Spaces.

    `uv export --group space --no-dev` resolves: main runtime + space group.
    `--no-emit-project` strips the workspace self-reference (HF Spaces' Gradio-SDK
    Dockerfile installs requirements.txt before copying the workspace, so an editable
    install isn't possible at that step — `app.py` instead adds `src/` to `sys.path`).
    """
    out = PROJECT_ROOT / "requirements.txt"
    subprocess.run(
        [
            "uv", "export",
            "--group", "space",
            "--no-dev",
            "--no-emit-project",
            "--no-hashes",
            "--format", "requirements-txt",
            "-o", str(out),
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Deploy the Gradio app to a HuggingFace Space.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--owner", default=DEFAULT_OWNER, help="HF user or org slug")
    ap.add_argument("--name", default=DEFAULT_NAME, help="Space repo name")
    ap.add_argument(
        "--private", action="store_true",
        help="Create as a private Space (default: public)",
    )
    ap.add_argument(
        "--commit-message", default="Deploy from local",
        help="Commit message for the upload",
    )
    args = ap.parse_args()

    if not SPACE_README_SRC.exists():
        sys.exit(
            f"Missing {SPACE_README_SRC} — the Space's README (with YAML frontmatter) "
            "must live at scripts/space_readme.md."
        )

    repo_id = f"{args.owner}/{args.name}"
    api = HfApi()

    if not os.environ.get("HF_TOKEN"):
        print(
            "ℹ️  HF_TOKEN not set in env — using the token saved by "
            "`hf auth login`. If you haven't logged in yet, do that first."
        )

    # 1) Build requirements.txt from the uv `space` group.
    print("→ Exporting space deps to requirements.txt ...")
    generate_requirements()

    # 2) Create the Space (idempotent).
    print(f"→ Ensuring Space exists: {repo_id} ...")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="gradio",
        private=args.private,
        exist_ok=True,
    )

    # 3) Upload the Space-specific README (with YAML frontmatter) as README.md.
    print(f"→ Uploading Space README from {SPACE_README_SRC.name} ...")
    api.upload_file(
        path_or_fileobj=str(SPACE_README_SRC),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="space",
        commit_message=args.commit_message,
    )

    # 4) Upload code + config (whitelist; everything else stays local).
    print("→ Uploading code + config ...")
    api.upload_folder(
        folder_path=str(PROJECT_ROOT),
        repo_id=repo_id,
        repo_type="space",
        allow_patterns=ALLOW_PATTERNS,
        ignore_patterns=IGNORE_PATTERNS,
        commit_message=args.commit_message,
    )

    url = f"https://huggingface.co/spaces/{repo_id}"
    print(f"\n✅ Deployed: {url}")
    print("   The Space rebuilds automatically; first build takes ~3 min.")


if __name__ == "__main__":
    main()
