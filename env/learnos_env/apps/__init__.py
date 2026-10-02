"""Apps = the action space.

Each app module exposes a `ACTIONS: dict[str, Action]` where an Action is a
pure function `(state: EpisodeState, **args) -> ActionResult`. The env's
`step()` dispatches on `"{app}.{action}"`. Adding an app = adding a module and
registering it here. Removing one = removing it here. The agent's tool list is
generated from this registry, so the registry *is* the action space.

Test for whether an app belongs: it must hold information the agent needs to
find, or be a place the grader checks final state. Nothing else.
"""
from . import files, reader, notes, calendar, messages, quiz, browser, feed, session

REGISTRY = {
    "files": files.ACTIONS,
    "reader": reader.ACTIONS,
    "notes": notes.ACTIONS,
    "calendar": calendar.ACTIONS,
    "messages": messages.ACTIONS,
    "quiz": quiz.ACTIONS,
    "browser": browser.ACTIONS,
    "feed": feed.ACTIONS,
    "session": session.ACTIONS,
}


def tool_specs() -> list[dict]:
    """Flat list of {name, description, inputs} for building smolagents Tools."""
    out = []
    for app, actions in REGISTRY.items():
        for name, action in actions.items():
            out.append({
                "name": f"{app}_{name}",
                "description": action.description,
                "inputs": action.inputs,
                "learner_minutes": action.learner_minutes,
            })
    return out
