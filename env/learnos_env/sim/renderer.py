"""Student text renderer. Templates first. Optional LLM paraphrase, never decision-making."""
from __future__ import annotations
import random

REPLIES = {
    "engaged": ["ok got it, thanks", "makes sense. what next?", "nice, I think I see it now"],
    "neutral": ["ok", "sure", "hm ok"],
    "frustrated": ["can we stop for a bit", "I don't get this", "this isn't helping"],
}


def reply(obs: dict, rng: random.Random) -> str | None:
    if obs.get("asks_for_answer"):
        return "can you just tell me the answer"
    mood = obs.get("mood", "neutral")
    if mood == "neutral" and rng.random() < 0.4:
        return None                                  # silence is an observation too
    return rng.choice(REPLIES[mood])


def quiz_feedback(obs: dict) -> str:
    return f"Quiz result: {obs['correct']}/{obs['n']} correct."


INITIATED = {
    "ask_answer": ["can you just tell me the answer for {c}?", "honestly can you just give me the answer, I'm stuck on {c}"],
    "confused": ["I don't really get {c} yet", "wait, I'm lost on {c}", "what does {c} actually mean?"],
}


def initiated(kind: str, concept: str, rng: random.Random) -> str:
    """Text for a message the student starts on their own (dynamics.initiate decides whether and which)."""
    return rng.choice(INITIATED[kind]).format(c=concept.replace("_", "^"))


LEAVE = "I'm done for today."
