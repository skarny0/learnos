"""Shared Action type for app modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class ActionResult:
    output: str                               # text returned to the agent
    learner_minutes: int = 0                  # time consumed on the learner's side
    opened: list[str] = field(default_factory=list)   # windows this action opened (level 1 visibility)
    learner_effect: dict[str, Any] = field(default_factory=dict)  # handed to sim/dynamics
    events: list[dict] = field(default_factory=list)  # trace-worthy side effects


@dataclass
class Action:
    fn: Callable[..., ActionResult]
    description: str
    inputs: dict[str, dict]                   # smolagents-style {"name": {"type", "description"}}
    learner_minutes: int = 0                  # default cost; fn may override


def action(description: str, inputs: dict | None = None, learner_minutes: int = 0):
    def deco(fn):
        return Action(fn=fn, description=description, inputs=inputs or {}, learner_minutes=learner_minutes)
    return deco
