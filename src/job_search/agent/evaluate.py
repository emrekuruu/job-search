from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai import Agent

from job_search.prompts import build_eval_system_prompt, build_eval_user
from job_search.providers import extract_reasoning, run_with_retry, teacher_model_settings
from job_search.schemas import FitEvaluation, JobListing

if TYPE_CHECKING:
    from pydantic_ai.models import Model

# The regex screen in filters.py catches what is a *fact* about a posting — its city, its
# language, its contract type. What's left needs reading: "5+ years of experience" and
# "you will own the roadmap for a team of eight" are seniority signals no pattern can spot.
#
# Bolted on here rather than folded into prompts.py, which is the single source of truth for
# the prompts the student model was distilled on. Changing those would silently move the
# Space's model off the distribution it was trained for. The agent runs the teacher, so it
# can afford a stricter, longer system prompt that the student never saw.
DISQUALIFIER_PROTOCOL = """

STEP 0 — DISQUALIFIER CHECK. Do this before you form any view of the candidate's fit.

The candidate's input may contain a section headed "HARD DISQUALIFIERS". If it does, read
the JOB POSTING first and test it against every rule listed there, one at a time.

If the posting hits ANY disqualifier:
  - Score 0-2 on every dimension.
  - Set overall_reasoning to a single short sentence naming the disqualifier that was hit.
  - Stop. Do not analyse the fit any further.

A disqualified role is disqualified no matter how well the candidate matches it otherwise.
This is the failure mode to guard against: a posting whose skills line up beautifully but
which asks for eight years of experience, or a level of seniority the candidate does not
have, is a rejection — not a 70. A strong match on a role the candidate cannot take is
worth nothing to them. Be strict about seniority in particular: judge it from what the
posting actually asks for (years of experience, scope, reports, "senior"/"lead"/"manager"
framing), not from how impressive the candidate is.

Only when NO disqualifier is hit do you carry out the full five-dimension evaluation
described above.
"""

_strict_eval_agent = Agent(
    output_type=FitEvaluation,
    system_prompt=build_eval_system_prompt() + DISQUALIFIER_PROTOCOL,
    retries=3,
)


async def evaluate_fit_strict(
    resume: str, job: JobListing, *, model: "Model"
) -> tuple[FitEvaluation, str]:
    """Evaluate one (resume, job) pair, honouring the candidate's HARD DISQUALIFIERS first."""
    result = await run_with_retry(
        _strict_eval_agent,
        build_eval_user(resume, job),
        model=model,
        model_settings=teacher_model_settings(),
    )
    return result.output, extract_reasoning(result)
