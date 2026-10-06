"""Load a materials pack into a Workspace, and apply L2 world events.

A pack is a folder under /instances/materials/<name>/ with:
  files/      markdown readings (path mirrors /course/...)
  notes.json  initial notes incl. the half-finished write-up
  calendar.json, messages.json, pages.json, quiz_bank.json, feed.json
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from .state import Workspace, FileNode, Note, CalendarEvent, Message, Page, Post, Instance

PACKS = Path(os.environ.get("LEARNOS_INSTANCES_DIR", "/instances")) / "materials"


def _headings(md: str) -> list[str]:
    return [l.lstrip("# ").strip() for l in md.splitlines() if l.startswith("#")]


def load(pack: str, instance: Instance) -> Workspace:
    root = PACKS / pack
    ws = Workspace()
    files_root = root / "files"
    if files_root.exists():
        for p in files_root.rglob("*"):
            rel = "/course/" + str(p.relative_to(files_root))
            if p.is_dir():
                ws.files[rel] = FileNode(path=rel, kind="dir")
            else:
                md = p.read_text()
                ws.files[rel] = FileNode(path=rel, kind="file", content=md, sections=_headings(md))
    ws.files.setdefault("/course", FileNode(path="/course", kind="dir"))
    for name, model, attr in (("notes.json", Note, "notes"), ("calendar.json", CalendarEvent, "calendar"), ("pages.json", Page, "pages")):
        f = root / name
        if f.exists():
            key = "id" if attr != "pages" else "url"
            setattr(ws, attr, {d[key]: model(**d) for d in json.loads(f.read_text())})
    f = root / "messages.json"
    if f.exists():
        ws.messages = [Message(**d) for d in json.loads(f.read_text())]
    f = root / "feed.json"
    if f.exists():
        ws.feed = [Post(**d) for d in json.loads(f.read_text())]
    return ws


def concepts(pack: str) -> dict:
    """Sim-side knowledge about the pack's concepts (concepts.json): which reading sections teach
    each one, and keywords a message needs to carry substance about it. Never shown to the agent."""
    f = PACKS / pack / "concepts.json"
    return json.loads(f.read_text()) if f.exists() else {}


def apply_event(ws: Workspace, ev: dict) -> None:
    """L2 world changes. Types: message | move_deadline | edit_note | break_page | post"""
    t = ev["type"]
    p = ev.get("payload", {})
    if t == "message":
        ws.messages.append(Message(id=f"ev{len(ws.messages)+1}", channel=p["channel"], author=p["author"], text=p["text"], t=ws.t))
    elif t == "move_deadline":
        e = ws.calendar.get(p["id"])
        if e:
            e.start = p["new_start"]
    elif t == "edit_note":
        n = ws.notes.get(p["note_id"])
        if n:
            n.body += "\n" + p["text"]
            n.modified_at = ws.t
    elif t == "break_page":
        ws.pages.pop(p["url"], None)
    elif t == "post":
        ws.feed.append(Post(id=f"ev-p{len(ws.feed)+1}", source=p["source"], text=p["text"], t=ws.t,
                            tag=p.get("tag", "noise"), concept=p.get("concept", "")))
