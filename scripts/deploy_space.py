"""Deploy one of the project's two Gradio Spaces.

  search  — the interactive demo. Upload a resume, watch the distilled student generate
            queries, scrape LinkedIn and score the matches live. Needs a GPU (ZeroGPU).
  results — the reader for the daily agent's bucket. Ranked matches + Reviewed/Applied
            ticks. No model, no scraping: runs on free cpu-basic.

Each Space owns its README (with YAML frontmatter) and its requirements.txt under
`scripts/spaces/<name>/`. The root README.md is the GitHub-facing project page and is
never uploaded.

Run:
  uv run python scripts/deploy_space.py --space search
  uv run python scripts/deploy_space.py --space results --bucket emrekuruu/job-agent
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from huggingface_hub import HfApi
except ImportError:
    sys.exit(
        "huggingface_hub is not installed. Run `uv sync` (it's in the dev group) and re-try."
    )

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OWNER = "emrekuruu"

IGNORE_PATTERNS = [
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.ruff_cache/**",
]

# Shared by both Spaces. `src/**/*.py` ships whole — the modules a given Space doesn't
# import (llama_cpp, jobspy) simply never load, and keeping one list avoids a Space
# breaking because a new shared module wasn't added to its allow-list.
_COMMON_ALLOW = ["pyproject.toml", "requirements.txt", ".python-version", "src/**/*.py"]


@dataclass(frozen=True)
class SpaceSpec:
    name: str
    app_file: str
    #: Space *variables* (public, non-secret). Values may be filled in from CLI args.
    variables: dict[str, str] = field(default_factory=dict)
    #: True when the Space writes to the Hub and therefore needs a write-scoped HF_TOKEN.
    needs_write_token: bool = False

    @property
    def config_dir(self) -> Path:
        return PROJECT_ROOT / "scripts" / "spaces" / self.key

    @property
    def key(self) -> str:
        return _KEY_BY_NAME[self.name]

    @property
    def allow_patterns(self) -> list[str]:
        return [self.app_file, *_COMMON_ALLOW]


SPACES: dict[str, SpaceSpec] = {
    "search": SpaceSpec(name="job-search-assistant", app_file="app.py"),
    "results": SpaceSpec(
        name="job-matches",
        app_file="app_results.py",
        needs_write_token=True,
    ),
}
_KEY_BY_NAME = {spec.name: key for key, spec in SPACES.items()}


def stage_requirements(spec: SpaceSpec) -> Path:
    """Copy the Space's requirements.txt to the repo root so the allow-list picks it up.

    NOT generated via `uv export`: the search Space's llama-cpp-python recipe relies on
    `--extra-index-url` directives that uv's exporter does not emit reliably. The two
    Spaces have deliberately different dependency sets — the results viewer ships none of
    the model/scraping stack — so the canonical lists live per-Space under scripts/spaces/.
    """
    src = spec.config_dir / "requirements.txt"
    if not src.exists():
        sys.exit(f"Missing {src} — each Space needs its own requirements.txt.")
    out = PROJECT_ROOT / "requirements.txt"
    shutil.copyfile(src, out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--space", required=True, choices=sorted(SPACES), help="Which Space to deploy")
    ap.add_argument("--owner", default=DEFAULT_OWNER, help="HF user or org slug")
    ap.add_argument("--name", default=None, help="Override the Space repo name")
    ap.add_argument(
        "--bucket", default=None,
        help="Bucket the results viewer reads, e.g. emrekuruu/job-agent (required for --space results)",
    )
    ap.add_argument("--private", action="store_true", help="Create as a private Space")
    ap.add_argument("--commit-message", default="Deploy from local")
    args = ap.parse_args()

    spec = SPACES[args.space]
    repo_id = f"{args.owner}/{args.name or spec.name}"

    readme = spec.config_dir / "README.md"
    if not readme.exists():
        sys.exit(f"Missing {readme} — the Space's README (with YAML frontmatter) must exist.")

    variables = dict(spec.variables)
    if args.space == "results":
        if not args.bucket:
            sys.exit("--space results needs --bucket (the viewer has nothing to read otherwise).")
        variables["JOB_AGENT_BUCKET"] = args.bucket

    token = os.environ.get("HF_TOKEN")
    if not token:
        print(
            "ℹ️  HF_TOKEN not set in env — using the token saved by `hf auth login` for the "
            "upload itself."
        )
    if spec.needs_write_token and not token:
        # The viewer writes status.json back to the bucket, so unlike the demo Space it
        # needs a token *of its own* at runtime. We can only forward one we can read.
        sys.exit(
            "--space results needs HF_TOKEN in your env: the viewer writes the "
            "Reviewed/Applied ticks back to the bucket, so the token has to be pushed to "
            "the Space as a secret. Export a write-scoped token and re-run."
        )

    api = HfApi()

    print(f"→ Staging requirements.txt from {spec.config_dir.relative_to(PROJECT_ROOT)} ...")
    stage_requirements(spec)

    print(f"→ Ensuring Space exists: {repo_id} ...")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="gradio",
        private=args.private,
        exist_ok=True,
    )

    for key, value in variables.items():
        print(f"→ Setting Space variable {key}={value} ...")
        api.add_space_variable(repo_id=repo_id, key=key, value=value)

    if spec.needs_write_token:
        print("→ Setting Space secret HF_TOKEN (needed to persist Reviewed/Applied ticks) ...")
        api.add_space_secret(repo_id=repo_id, key="HF_TOKEN", value=token)

    print(f"→ Uploading Space README from {readme.relative_to(PROJECT_ROOT)} ...")
    api.upload_file(
        path_or_fileobj=str(readme),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="space",
        commit_message=args.commit_message,
    )

    print("→ Uploading code + config ...")
    api.upload_folder(
        folder_path=str(PROJECT_ROOT),
        repo_id=repo_id,
        repo_type="space",
        allow_patterns=spec.allow_patterns,
        ignore_patterns=IGNORE_PATTERNS,
        commit_message=args.commit_message,
    )

    url = f"https://huggingface.co/spaces/{repo_id}"
    print(f"\n✅ Deployed: {url}")
    if args.space == "search":
        print("   Reminder: ZeroGPU must be selected in the Space's Settings — the frontmatter")
        print("   cannot assign hardware. First build takes ~3 min.")


if __name__ == "__main__":
    main()
