"""Browser app: local course site. Stale vs current info; one link breaks at L2."""
from __future__ import annotations
from ._base import action, ActionResult
from ..state import EpisodeState

S = {"type": "string"}


@action("Visit a course site page.", {"url": {**S, "description": "e.g. course://schedule, course://assignments"}})
def visit(state: EpisodeState, url: str) -> ActionResult:
    p = state.workspace.pages.get(url)
    if not p:
        return ActionResult(output=f"404: {url}")
    return ActionResult(output=f"# {p.title}\n{p.content}", opened=[f"browser:{url}"])


ACTIONS = {"visit": visit}
