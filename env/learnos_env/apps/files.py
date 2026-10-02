"""Files app: the course folder. Holds readings, past write-ups, the current draft."""
from __future__ import annotations
from ._base import action, ActionResult
from ..state import EpisodeState

S = {"type": "string"}


@action("List files and folders at a path in the student's course folder.",
        {"path": {**S, "description": "Folder path, e.g. /course"}})
def ls(state: EpisodeState, path: str = "/course") -> ActionResult:
    ws = state.workspace
    prefix = path.rstrip("/") + "/"
    children = sorted({p[len(prefix):].split("/")[0] for p in ws.files if p.startswith(prefix) and p != path})
    if not children and path not in ws.files:
        return ActionResult(output=f"No such folder: {path}")
    return ActionResult(output="\n".join(children) or "(empty)", opened=[f"files:{path}"])


@action("Search file names and contents for a keyword.",
        {"query": {**S, "description": "Keyword or phrase"}})
def search(state: EpisodeState, query: str) -> ActionResult:
    q = query.lower()
    hits = [p for p, f in state.workspace.files.items() if f.kind == "file" and (q in p.lower() or q in f.content.lower())]
    return ActionResult(output="\n".join(hits[:20]) or "No matches.")


@action("Return the section headings of a file so you can open one at a time.",
        {"path": {**S, "description": "File path"}})
def outline(state: EpisodeState, path: str) -> ActionResult:
    f = state.workspace.files.get(path)
    if not f or f.kind != "file":
        return ActionResult(output=f"No such file: {path}")
    return ActionResult(output="\n".join(f.sections) or "(no headings)", opened=[f"files:{path}"])


ACTIONS = {"ls": ls, "search": search, "outline": outline}
