"""Notes app: the student's notes and the weekly build write-up draft."""
from __future__ import annotations
from ._base import action, ActionResult
from ..state import EpisodeState, Note

S = {"type": "string"}


@action("List the student's notes.")
def list_notes(state: EpisodeState) -> ActionResult:
    return ActionResult(output="\n".join(f"{n.id}: {n.title}" for n in state.workspace.notes.values()) or "(none)",
                        opened=["notes:list"])


@action("Read a note by id.", {"note_id": {**S, "description": "Note id"}})
def read(state: EpisodeState, note_id: str) -> ActionResult:
    n = state.workspace.notes.get(note_id)
    return ActionResult(output=n.body if n else f"No such note: {note_id}", opened=[f"notes:{note_id}"])


@action("Append text to a note (e.g. add a scaffold to the write-up). The student sees this edit.",
        {"note_id": {**S, "description": "Note id"}, "text": {**S, "description": "Text to append"}})
def append(state: EpisodeState, note_id: str, text: str) -> ActionResult:
    n = state.workspace.notes.get(note_id)
    if not n:
        return ActionResult(output=f"No such note: {note_id}")
    n.body += "\n" + text
    n.modified_at = state.workspace.t
    return ActionResult(output="Appended.", events=[{"type": "note_edit", "note_id": note_id, "by": "agent"}])


ACTIONS = {"list": list_notes, "read": read, "append": append}
