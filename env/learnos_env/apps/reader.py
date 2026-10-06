"""Reader app: shows a reading section TO THE STUDENT. This is a learning action."""
from __future__ import annotations
from ._base import action, ActionResult
from ..state import EpisodeState

S = {"type": "string"}


@action("Open one section of a reading for the student. Costs ~5 learner-minutes. "
        "The student reads it (or skims, if attention is low).",
        {"path": {**S, "description": "File path"},
         "section": {**S, "description": "Section heading, from files_outline"},
         "concept": {**S, "description": "Concept id this section teaches"}},
        learner_minutes=5)
def open_section(state: EpisodeState, path: str, section: str, concept: str) -> ActionResult:
    f = state.workspace.files.get(path)
    if not f or section not in f.sections:
        return ActionResult(output=f"Section not found: {path}#{section}")
    # TODO: slice content by heading
    text = f.content
    return ActionResult(
        output=f"Student is reading '{section}' ({len(text.split())} words).",
        learner_minutes=5,
        opened=[f"reader:{path}#{section}"],
        learner_effect={"kind": "read", "concept": concept, "section": section, "minutes": 5},
    )


@action("Read a section yourself (agent-only, no learner time). Use to decide what to assign.",
        {"path": {**S, "description": "File path"}, "section": {**S, "description": "Section heading"}})
def peek_section(state: EpisodeState, path: str, section: str) -> ActionResult:
    f = state.workspace.files.get(path)
    if not f:
        return ActionResult(output=f"No such file: {path}")
    return ActionResult(output=f.content[:1500])   # TODO: slice by heading


ACTIONS = {"open_section": open_section, "peek_section": peek_section}
