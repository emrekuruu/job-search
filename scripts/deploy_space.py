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
        "huggingface_hub is not installed. Run `uv sync` (it's in the dev group) "
        "and re-try."
    )

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OWNER = "build-small-hackathon"   # https://huggingface.co/build-small-hackathon
DEFAULT_NAME = "job-search-assistant"

# Files shipped to the Space. Everything else stays local (data/, .env, modal_apps/, etc.).
ALLOW_PATTERNS = [
    "app.py",
    "README.md",
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


def generate_requirements() -> Path:
    """Export the locked `space` group deps to requirements.txt for HF Spaces.

    `uv export --group space --no-dev` resolves: main runtime + space group.
    `-e .` is appended so HF's pip install picks up the project (src layout).
    """
    out = PROJECT_ROOT / "requirements.txt"
    subprocess.run(
        [
            "uv", "export",
            "--group", "space",
            "--no-dev",
            "--no-hashes",
            "--format", "requirements-txt",
            "-o", str(out),
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )
    text = out.read_text()
    if "-e ." not in text:
        out.write_text(text.rstrip() + "\n-e .\n")
    return out


def get_deepseek_key() -> str | None:
    """Read DEEPSEEK_API_KEY from env first, then local .env. No silent fallback."""
    if v := os.environ.get("DEEPSEEK_API_KEY"):
        return v
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("DEEPSEEK_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Deploy the Gradio app to a HuggingFace Space.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument(
        "--owner", default=DEFAULT_OWNER,
        help="HF user or org slug to deploy under",
    )
    ap.add_argument("--name", default=DEFAULT_NAME, help="Space repo name")
    ap.add_argument(
        "--private", action="store_true",
        help="Create as a private Space (default: public)",
    )
    ap.add_argument(
        "--skip-secret", action="store_true",
        help="Don't push DEEPSEEK_API_KEY to the Space; set it manually instead",
    )
    ap.add_argument(
        "--commit-message", default="Deploy from local",
        help="Commit message for the upload",
    )
    args = ap.parse_args()

    repo_id = f"{args.owner}/{args.name}"
    api = HfApi()

    if not os.environ.get("HF_TOKEN"):
        print(
            "ℹ️  HF_TOKEN not set in env — using the token saved by "
            "`huggingface-cli login`. If you haven't logged in yet, do that first."
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

    # 3) Push DEEPSEEK_API_KEY as a Space secret (so the deployed app can call DeepSeek).
    if not args.skip_secret:
        ds_key = get_deepseek_key()
        if ds_key:
            print("→ Syncing DEEPSEEK_API_KEY secret to the Space ...")
            api.add_space_secret(repo_id=repo_id, key="DEEPSEEK_API_KEY", value=ds_key)
        else:
            print(
                "⚠️  DEEPSEEK_API_KEY not found in env or local .env — "
                "set it manually in the Space Settings before the first run."
            )

    # 4) Upload project files (whitelist; everything else stays local).
    print("→ Uploading files ...")
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
