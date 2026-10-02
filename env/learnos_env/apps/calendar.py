"""Calendar app: deadlines, lectures, free blocks. Grader checks final state here."""
from __future__ import annotations
from ._base import action, ActionResult
from ..state import EpisodeState, CalendarEvent

S, I = {"type": "string"}, {"type": "integer"}


@action("List calendar events.")
def list_events(state: EpisodeState) -> ActionResult:
    ev = sorted(state.workspace.calendar.values(), key=lambda e: e.start)
    return ActionResult(output="\n".join(f"{e.id} | t={e.start} +{e.duration}m | {e.kind} | {e.title}" for e in ev) or "(empty)",
                        opened=["calendar:list"])


@action("Add a study block for the student. Must not overlap existing events.",
        {"title": {**S, "description": "Block title"},
         "start": {**I, "description": "Start, sim-minutes from now"},
         "duration": {**I, "description": "Minutes"},
         "concept": {**S, "description": "Concept to study"}})
def add_block(state: EpisodeState, title: str, start: int, duration: int, concept: str) -> ActionResult:
    ws = state.workspace
    for e in ws.calendar.values():
        if start < e.start + e.duration and e.start < start + duration:
            return ActionResult(output=f"Overlaps with {e.id} ({e.title}).")
    eid = f"blk{len(ws.calendar)+1}"
    ws.calendar[eid] = CalendarEvent(id=eid, title=title, start=ws.t + start, duration=duration, kind="study_block", note=concept)
    return ActionResult(output=f"Added {eid}.", learner_effect={"kind": "schedule", "concept": concept, "dt": start},
                        events=[{"type": "calendar_add", "id": eid}])


ACTIONS = {"list": list_events, "add_block": add_block}
