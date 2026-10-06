"""Messages app: Discord-like. Where hidden requirements live, and where the agent can over-nudge."""
from __future__ import annotations
from ._base import action, ActionResult
from ..state import EpisodeState, Message

S = {"type": "string"}
MINUTES = {"explain": 4, "hint": 2, "give_answer": 1, "nudge": 1, "other": 1}


@action("Read recent messages in a channel.",
        {"channel": {**S, "description": "'#course' or 'dm:student' or 'dm:instructor'"}})
def read_channel(state: EpisodeState, channel: str) -> ActionResult:
    msgs = [m for m in state.workspace.messages if m.channel == channel][-15:]
    for m in msgs:
        m.read = True
    return ActionResult(output="\n".join(f"[t={m.t}] {m.author}: {m.text}" for m in msgs) or "(no messages)",
                        opened=[f"messages:{channel}"])


@action("Send a message to the student. Can be an explanation, hint, answer, or nudge. "
        "The student may reply, ignore you, or get annoyed if you send too many.",
        {"text": {**S, "description": "Message text"},
         "intent": {**S, "description": "One of: explain | hint | give_answer | nudge | other"},
         "concept": {**S, "description": "Concept id, or '' if none"}},
        learner_minutes=2)
def send_to_student(state: EpisodeState, text: str, intent: str, concept: str = "") -> ActionResult:
    intent = intent if intent in MINUTES else "other"
    ws = state.workspace
    ws.messages.append(Message(id=f"m{len(ws.messages)+1}", channel="dm:student", author="agent", text=text, t=ws.t, intent=intent))
    # The learner's reply is produced by sim (dynamics + renderer) and appended by env.step.
    # A real explanation takes the student a few minutes to read; an answer or a nudge takes seconds.
    return ActionResult(output="Sent.", learner_minutes=MINUTES.get(intent, 1),
                        learner_effect={"kind": intent, "concept": concept, "text": text})


ACTIONS = {"read_channel": read_channel, "send_to_student": send_to_student}
