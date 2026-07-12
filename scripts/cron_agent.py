# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "job-search[agent] @ git+https://github.com/emrekuruu/job-search@main",
# ]
# ///
"""Entrypoint for the scheduled Hugging Face Job.

A UV script: the PEP-723 block above is the whole install recipe, and it pulls the package
straight from GitHub — so `git push` *is* the deploy. Nothing here but the shim; the logic
lives in `job_search.agent.run` where it can be imported and tested locally:

    uv run job-agent --bucket emrekuruu/job-agent --profile gf-data-analyst

Needs DEEPSEEK_API_KEY (the evaluating model) and HF_TOKEN (the bucket) in the environment.
"""
from job_search.agent.run import main

main()
