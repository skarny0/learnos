"""Canonical state models.

Rule: everything the agent could ever see lives in `Workspace`. Everything it
must never see lives in `LearnerState`. `EpisodeState` holds both plus
bookkeeping. The observation builder (env.py) only ever serializes `Workspace`,
filtered by observability level.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

# ----------------------------------------------------------------- visible --


class FileNode(BaseModel):
    path: str                      # "/course/readings/week3/attention.md"
    kind: Literal["file", "dir"]
    content: str = ""              # markdown for files; "" for dirs
    sections: list[str] = []       # headings, so Reader can open one at a time
    modified_at: int = 0           # sim-minutes


class Note(BaseModel):
    id: str
    title: str
    body: str
    modified_at: int = 0


class CalendarEvent(BaseModel):
    id: str
    title: str
    start: int                     # sim-minutes from episode t0
    duration: int                  # minutes
    kind: Literal["lecture", "deadline", "study_block", "other"] = "other"
    note: str = ""


class Message(BaseModel):
    id: str
    channel: str                   # "#course", "dm:student", "dm:instructor"
    author: str                    # "instructor" | "student" | "agent" | peer name
    text: str
    t: int                         # sim-minutes
    read: bool = False
    intent: str = ""               # agent messages: the agent's own label (explain|hint|give_answer|nudge|other)


class QuizItem(BaseModel):
    id: str
    concept: str
    difficulty: float              # 0..1
    stem: str
    answer: str


class QuizResult(BaseModel):
    concept: str
    n: int
    correct: int
    difficulty: float
    t: int
    aided: bool = False            # was help given on this concept this session?


class Page(BaseModel):
    url: str                       # "course://schedule"
    title: str
    content: str
    stale: bool = False            # L2: conflicts with Messages


class Post(BaseModel):
    """Social feed post. The student scrolls these; the agent can read and mute sources."""
    id: str
    source: str                    # "#memes", "@peer_a", ...
    text: str
    t: int                         # sim-minutes; posts with t > now are not yet published
    tag: Literal["relevant", "misinfo", "noise"] = Field("noise", exclude=True)   # grader-only, never serialized


class ActivityEvent(BaseModel):
    """What the activity tracker reports. Screen-level only: it cannot see attention, and
    off-screen phone use shows up as 'idle'. Noisy by design (a proxy, not ground truth)."""
    t: int                         # sim-minutes at start of the chunk
    app: str                       # reader | messages | quiz | feed | idle | notes | ...
    minutes: int = 0
    detail: str = ""


class Workspace(BaseModel):
    """Everything the agent may observe (subject to level)."""
    t: int = 0                                      # sim clock, minutes
    files: dict[str, FileNode] = {}
    notes: dict[str, Note] = {}
    calendar: dict[str, CalendarEvent] = {}
    messages: list[Message] = []
    quiz_log: list[QuizResult] = []
    pages: dict[str, Page] = {}
    open_windows: list[str] = []                    # e.g. ["files:/course", "notes:writeup"]
    student_activity: list[ActivityEvent] = []      # streamed tracker reports (proxy)
    feed: list[Post] = []                           # all posts incl. scheduled; filter on t <= now
    feed_muted: list[str] = []                      # sources muted by the agent; "all" mutes everything


# ------------------------------------------------------------------ hidden --


class LearnerState(BaseModel):
    """Hidden. Numeric only. Updated exclusively by sim/dynamics.py."""
    concepts: list[str]
    p_know: dict[str, float]       # deep mastery, drives post-test
    p_perf: dict[str, float]       # recognition after help; resets per session
    half_life_h: dict[str, float]  # memory half-life per concept
    attention: float = 0.8
    motivation: float = 0.7
    reliance: float = 0.0          # grows with give_answer
    persistence: float = 0.75
    persona: dict = {}             # learn_rate, slip, guess, fatigue_rate, distraction_rate
    off_task_streak: int = 0       # minutes off task in a row (makes drifting sticky)
    feed_minutes: float = 0.0      # true time on the feed (tracker sees most of it)
    phone_minutes: float = 0.0     # true off-screen phone time (tracker reports 'idle')


# --------------------------------------------------------------- bookkeeping --


class Budget(BaseModel):
    agent_steps: int = 30
    learner_minutes: int = 90
    sessions: int = 1


class Instance(BaseModel):
    instance_id: str
    seed: int
    level: Literal[0, 1, 2] = 1
    instruction: str
    concepts: list[str]
    budget: Budget = Budget()
    materials_pack: str = "default"   # folder under /instances/materials
    learner_profile: dict = {}
    events: list[dict] = []           # L2 scheduled world changes {t, type, payload}


class EpisodeState(BaseModel):
    instance: Instance
    workspace: Workspace
    learner: Optional[LearnerState]   # None in live mode
    baseline_learner: Optional[LearnerState]
    step: int = 0
    done: bool = False
    termination: Optional[str] = None
    mode: Literal["sim", "live"] = "sim"
