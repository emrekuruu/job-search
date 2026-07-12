"""Schedule the daily job-search agent for one profile as a Hugging Face Job.

One scheduled Job **per profile** — so `gf-data-analyst` and `gf-product` run on their own
cadences and a failure in one never silently stops the other.

Run:
  uv run python scripts/deploy_cron.py --bucket emrekuruu/job-agent --profile gf-data-analyst
  uv run python scripts/deploy_cron.py --bucket emrekuruu/job-agent --profile gf-product --schedule "0 7 * * *"

Requires HF_TOKEN and DEEPSEEK_API_KEY in your environment: both are forwarded to the Job
as encrypted secrets (the Job needs the bucket and the evaluating model, respectively).
Jobs are pay-as-you-go and need a positive credit balance:
https://huggingface.co/settings/billing
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    from huggingface_hub import HfApi
except ImportError:
    sys.exit("huggingface_hub is not installed. Run `uv sync` and re-try.")

# The Job installs the package from GitHub via the PEP-723 block in cron_agent.py, so the
# deployed code is whatever is on `main` — `git push` is the deploy.
SCRIPT_URL = "https://raw.githubusercontent.com/emrekuruu/job-search/main/scripts/cron_agent.py"

# cpu-basic ($0.01/hr) is all this needs: the evaluating model is DeepSeek's API, so the Job
# itself only scrapes, orchestrates and writes a spreadsheet.
FLAVOR = "cpu-basic"
# Generous on purpose. The evaluations are fast (fanned out across teacher_concurrency), but
# the LinkedIn scrape is serial and paced — a profile asking for 50 new jobs can walk several
# rounds x several queries x 30 descriptions before it fills the batch, and the worst case is
# months in, when nearly everything scraped is already evaluated. At $0.01/hr a loose ceiling
# is free; a Job killed at the 30m default halfway through is not.
TIMEOUT = "2h"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--bucket", required=True, help="e.g. emrekuruu/job-agent")
    ap.add_argument("--profile", required=True, help="e.g. gf-data-analyst")
    ap.add_argument(
        "--schedule", default="@daily",
        help="@daily/@hourly/... or CRON, e.g. '0 7 * * *' for 7am UTC",
    )
    ap.add_argument("--script-url", default=SCRIPT_URL)
    ap.add_argument("--flavor", default=FLAVOR)
    ap.add_argument("--timeout", default=TIMEOUT)
    args = ap.parse_args()

    missing = [k for k in ("HF_TOKEN", "DEEPSEEK_API_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(
            f"Missing {', '.join(missing)} in the environment. Both are forwarded to the Job "
            "as secrets — it can't reach the bucket or the model without them."
        )

    api = HfApi()
    job = api.create_scheduled_uv_job(
        script=args.script_url,
        script_args=["--bucket", args.bucket, "--profile", args.profile],
        schedule=args.schedule,
        flavor=args.flavor,
        timeout=args.timeout,
        secrets={
            "HF_TOKEN": os.environ["HF_TOKEN"],
            "DEEPSEEK_API_KEY": os.environ["DEEPSEEK_API_KEY"],
        },
        labels={"app": "job-agent", "profile": args.profile},
    )

    print(f"✅ Scheduled '{args.profile}' ({args.schedule}, {args.flavor})")
    print(f"   id: {job.id}")
    print("\n   Run it now instead of waiting:")
    print(f"     hf jobs scheduled trigger {job.id}")
    print("   Inspect / pause / remove:")
    print("     hf jobs scheduled ps")
    print(f"     hf jobs scheduled suspend {job.id}")
    print(f"     hf jobs scheduled delete {job.id}")


if __name__ == "__main__":
    main()
