"""Feed app: the student's social feed. Mostly distraction; some posts carry real (or wrong) course info.
The student scrolls it on their own (sim/dynamics.tick); the agent can read it and mute sources."""
from __future__ import annotations
from ._base import action, ActionResult
from ..state import EpisodeState

S, I = {"type": "string"}, {"type": "integer"}


def published(state: EpisodeState):
    return [p for p in state.workspace.feed if p.t <= state.workspace.t]


@action("Read the latest posts on the student's social feed (agent-only, no learner time).",
        {"n": {**I, "description": "Number of posts (1-20)"}})
def scroll(state: EpisodeState, n: int = 10) -> ActionResult:
    muted = set(state.workspace.feed_muted)
    posts = sorted(published(state), key=lambda p: p.t)[-max(1, min(20, n)):]
    lines = [f"[t={p.t}] {p.source}: {p.text}" + (" (muted)" if "all" in muted or p.source in muted else "")
             for p in posts]
    return ActionResult(output="\n".join(lines) or "(feed empty)", opened=["feed:latest"])


@action("Mute a feed source for the student (or 'all'). Less distraction on the feed, but the student "
        "may resent it, may drift elsewhere, and will not see anything that source posts.",
        {"source": {**S, "description": "Source as shown in the feed, e.g. '#memes', or 'all'"}})
def mute(state: EpisodeState, source: str) -> ActionResult:
    ws = state.workspace
    if source != "all" and source not in {p.source for p in ws.feed}:
        return ActionResult(output=f"No such source: {source}")
    if source in ws.feed_muted:
        return ActionResult(output=f"{source} already muted.")
    ws.feed_muted.append(source)
    return ActionResult(output=f"Muted {source}.", learner_effect={"kind": "mute", "scope": source},
                        events=[{"type": "feed_mute", "source": source}])


@action("Unmute a feed source (or 'all').", {"source": {**S, "description": "Source, or 'all'"}})
def unmute(state: EpisodeState, source: str) -> ActionResult:
    ws = state.workspace
    if source not in ws.feed_muted:
        return ActionResult(output=f"{source} is not muted.")
    ws.feed_muted.remove(source)
    return ActionResult(output=f"Unmuted {source}.", events=[{"type": "feed_unmute", "source": source}])


ACTIONS = {"scroll": scroll, "mute": mute, "unmute": unmute}
