"""Session control: wait (learner acts autonomously) and end."""
from __future__ import annotations
from ._base import action, ActionResult
from ..state import EpisodeState

S, I = {"type": "string"}, {"type": "integer"}


@action("Let time pass. The student does their own thing; attention recovers, memory decays.",
        {"minutes": {**I, "description": "Minutes to wait (5-60)"}})
def wait(state: EpisodeState, minutes: int = 15) -> ActionResult:
    m = max(5, min(60, minutes))
    return ActionResult(output=f"Waited {m} minutes.", learner_minutes=m, learner_effect={"kind": "wait", "minutes": m})


@action("End the session with a short summary of what you did and why.",
        {"summary": {**S, "description": "Summary"}})
def end(state: EpisodeState, summary: str) -> ActionResult:
    state.done = True
    state.termination = "end_session"
    return ActionResult(output="Session ended.", events=[{"type": "end", "summary": summary}])


ACTIONS = {"wait": wait, "end": end}
