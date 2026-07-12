from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi

from job_search.config import settings

# Names inside a profile folder.
RESUME = "resume.pdf"
CONFIG = "config.json"
EVALUATIONS = "evaluations.jsonl"
STATUS = "status.json"
REPORT = "evaluations.xlsx"


def get_api() -> HfApi:
    """An HfApi bound to *our* token.

    Never `HfApi()`: with no token it silently falls back to whatever account
    `hf auth login` cached, which on a dev machine is routinely not the account that owns
    the bucket. A wrong-namespace write is the kind of failure that looks like success.
    """
    if not settings.hf_token:
        raise ValueError("HF_TOKEN is not set; required to reach the bucket.")
    return HfApi(token=settings.hf_token)


class ProfileStore:
    """Read/write one profile's folder in a Hugging Face Storage Bucket.

    Layout: ``profiles/<profile>/{resume.pdf, config.json, evaluations.jsonl,
    status.json, evaluations.xlsx, runs/<utc-ts>.json}``

    **File ownership is the concurrency design and must not be violated.** The daily
    agent owns `evaluations.jsonl`, `evaluations.xlsx` and `runs/`; the results Space
    owns `status.json`. A bucket is last-write-wins whole-file object storage, so two
    writers on the same file would silently clobber each other. Keeping the ticks out
    of `evaluations.jsonl` is what makes the two safe to run concurrently.
    """

    def __init__(self, bucket: str, profile: str, api: HfApi | None = None) -> None:
        self.bucket = bucket
        self.profile = profile
        self.api = api if api is not None else get_api()

    def key(self, name: str) -> str:
        """Bucket-relative path of `name` inside this profile's folder."""
        return f"profiles/{self.profile}/{name}"

    def uri(self, name: str) -> str:
        return f"hf://buckets/{self.bucket}/{self.key(name)}"

    def list_names(self) -> set[str]:
        """Names present in this profile's folder (top level, relative to the folder)."""
        prefix = f"profiles/{self.profile}/"
        return {
            item.path.removeprefix(prefix)
            for item in self.api.list_bucket_tree(self.bucket, prefix=prefix, recursive=True)
            if item.type == "file"
        }

    def download(self, name: str, dest: Path) -> None:
        """Download a REQUIRED file. Raises if it isn't in the bucket."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.api.download_bucket_files(
            self.bucket, files=[(self.key(name), str(dest))], raise_on_missing_files=True
        )

    def download_optional(self, name: str, dest: Path) -> bool:
        """Download a file that legitimately may not exist yet.

        Only `evaluations.jsonl` and `status.json` qualify: on a profile's very first run
        neither exists, and that is a defined initial state rather than an error. Returns
        True if the file was fetched.
        """
        if name not in self.list_names():
            return False
        self.download(name, dest)
        return True

    def upload(self, items: list[tuple[bytes | Path, str]]) -> None:
        """Upload files. Each item is (bytes-or-local-path, name-within-the-profile-folder)."""
        self.api.batch_bucket_files(
            self.bucket,
            add=[
                (str(src) if isinstance(src, Path) else src, self.key(name))
                for src, name in items
            ],
        )

    def read_json(self, name: str, workdir: Path) -> dict[str, Any]:
        """Download and parse a REQUIRED json file."""
        dest = workdir / name
        self.download(name, dest)
        return json.loads(dest.read_text(encoding="utf-8"))

    def read_json_optional(self, name: str, workdir: Path) -> dict[str, Any]:
        """Parse a json file that may not exist yet; `{}` if absent (see download_optional)."""
        dest = workdir / name
        if not self.download_optional(name, dest):
            return {}
        return json.loads(dest.read_text(encoding="utf-8"))

    def write_json(self, name: str, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.upload([(body, name)])


def list_profiles(bucket: str, api: HfApi | None = None) -> list[str]:
    """Every profile id that has a config.json in the bucket."""
    api = api if api is not None else get_api()
    profiles: list[str] = []
    for item in api.list_bucket_tree(bucket, prefix="profiles/", recursive=True):
        if item.type == "file" and item.path.endswith(f"/{CONFIG}"):
            profiles.append(item.path.removeprefix("profiles/").removesuffix(f"/{CONFIG}"))
    return sorted(profiles)
