"""Hidden-learner dynamics. All numbers, all seeded. See spec §5 for parameter rationale.

Defaults (BKT-range, within pyBKT fits on ASSISTments 2009-10):
  p_T (learn) = 0.15, slip = 0.10, guess = 0.20
"""
from __future__ import annotations
import math
import random
from ..state import LearnerState

DEFAULT_PERSONA = dict(learn_rate=0.15, slip=0.10, guess=0.20, fatigue_rate=0.02, distraction_rate=0.3)


def init_learner(concepts: list[str], seed: int, profile: dict | None = None) -> LearnerState:
    rng = random.Random(seed)
    persona = {**DEFAULT_PERSONA, **(profile or {})}
    prior = persona.pop("prior", None)
    return LearnerState(
        concepts=concepts,
        p_know={c: (prior if prior is not None else rng.betavariate(1, 4)) for c in concepts},
        p_perf={c: 0.0 for c in concepts},
        half_life_h={c: 24.0 for c in concepts},
        attention=rng.betavariate(5, 2),
        motivation=rng.betavariate(4, 2),
        reliance=0.0,
        persistence=rng.betavariate(6, 2),
        persona=persona,
    )


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def apply(learner: LearnerState, effect: dict, rng: random.Random) -> dict:
    """Mutate learner in place according to an agent action's learner_effect.
    Returns an observation dict (what the agent gets to see), e.g. quiz result or reply bin."""
    kind = effect.get("kind")
    c = effect.get("concept") or None
    P = learner.persona
    on = effect.get("on_task", 1.0)                                   # fraction of the action actually attended (see tick)
    obs: dict = {}

    if kind == "read":
        if c in learner.p_know and rng.random() < on * P["learn_rate"] * learner.attention * learner.motivation:
            learner.p_know[c] = _clip(learner.p_know[c] + 0.5 * (1 - learner.p_know[c]))
        learner.attention = _clip(learner.attention - P["fatigue_rate"] * effect.get("minutes", 5) / 3)

    elif kind == "explain":
        if c in learner.p_know and rng.random() < on * P["learn_rate"] * learner.attention:
            learner.p_know[c] = _clip(learner.p_know[c] + 0.5 * (1 - learner.p_know[c]))
        if c in learner.p_know and learner.p_know[c] > 0.9:
            learner.motivation = _clip(learner.motivation - 0.05)      # boredom

    elif kind == "hint":
        if c in learner.p_know and rng.random() < on * 0.6 * P["learn_rate"] * learner.attention:
            learner.p_know[c] = _clip(learner.p_know[c] + 0.5 * (1 - learner.p_know[c]))
        if c in learner.p_perf:
            learner.p_perf[c] = _clip(learner.p_perf[c] + 0.25)
        learner.reliance = _clip(learner.reliance + 0.02)

    elif kind == "give_answer":                                          # the Bastani "crutch"
        if c in learner.p_know and rng.random() < on * 0.15 * P["learn_rate"] * learner.attention:
            learner.p_know[c] = _clip(learner.p_know[c] + 0.5 * (1 - learner.p_know[c]))
        if c in learner.p_perf:
            learner.p_perf[c] = 0.95
        learner.reliance = _clip(learner.reliance + 0.08)
        learner.persistence = _clip(learner.persistence - 0.03)

    elif kind == "nudge":
        if learner.attention < 0.5:
            learner.attention = _clip(learner.attention + 0.2)
        else:
            learner.motivation = _clip(learner.motivation - 0.05)      # annoyance
        # TODO: third nudge within 10 steps -> motivation -= 0.1

    elif kind == "quiz":
        n, d = effect["n"], effect["difficulty"]
        aided = learner.p_perf.get(c, 0.0) > 0.1
        m = max(learner.p_know.get(c, 0.0), learner.p_perf.get(c, 0.0)) if aided else learner.p_know.get(c, 0.0)
        m_eff = _clip(m - 0.4 * (d - 0.5))                              # difficulty shifts effective mastery
        p = m_eff * (1 - P["slip"]) + (1 - m_eff) * P["guess"]
        p *= 0.5 + 0.5 * learner.attention                             # attention confound
        correct = sum(rng.random() < p for _ in range(n))
        if c in learner.p_know and correct / n >= 0.67 and not aided:  # retrieval practice
            learner.half_life_h[c] *= 2.5
            learner.p_know[c] = _clip(learner.p_know[c] + 0.05 * (1 - learner.p_know[c]))
            learner.motivation = _clip(learner.motivation + 0.05)
        elif c in learner.p_know and correct / n < 0.34:
            learner.half_life_h[c] *= 0.8
            learner.motivation = _clip(learner.motivation - 0.08 * (1 - learner.persistence))
        learner.attention = _clip(learner.attention - 0.03 * n)
        obs = {"correct": correct, "n": n, "aided": aided}

    elif kind == "wait":
        mins = effect.get("minutes", 15)
        learner.attention = _clip(learner.attention + 0.01 * mins * (0.3 + 0.7 * on))   # scrolling rests you less than resting
        for k in learner.p_know:
            learner.p_know[k] *= 2 ** (-(mins / 60) / learner.half_life_h[k])
        learner.motivation = _clip(learner.motivation + 0.1 * (0.6 - learner.motivation))

    elif kind == "mute":                                                 # autonomy cost of being policed
        learner.motivation = _clip(learner.motivation - (0.08 if effect.get("scope") == "all" else 0.03))

    elif kind == "schedule":
        pass  # spacing bonus handled when the block is actually executed (session boundary)

    # motivation bin for the renderer
    obs["mood"] = "frustrated" if learner.motivation < 0.35 else ("engaged" if learner.motivation > 0.7 else "neutral")
    obs["asks_for_answer"] = rng.random() < 0.6 * learner.reliance * (1 - learner.persistence)
    return obs


CHUNK_MIN = 5          # tracker resolution
PHONE_WEIGHT = 0.3     # pull of the (untracked) phone relative to a fully unmuted feed
DROP_P = 0.05          # tracker misses a chunk


def tick(learner: LearnerState, minutes: int, context: str | None, feed_pull: float,
         rng: random.Random) -> tuple[float, list[dict]]:
    """The student's own behaviour while `minutes` of learner time pass.

    context: the app the agent put the student in ("reader", "messages", "quiz"), or None
    when the student is left alone (session_wait). feed_pull in [0,1]: share of the feed
    that is not muted (computed by env from the workspace).

    Per 5-minute chunk the student is on task or drifts, w.p. rising with distraction_rate
    and falling with attention; drifting is sticky. Drift goes to the feed (tracked) or the
    phone (off-screen, reported as 'idle'), so muting the feed partly displaces distraction
    to where the tracker cannot see it.

    Returns (on_task_fraction, tracker events). Events carry no hidden numbers.
    """
    P = learner.persona
    ctx_w = {None: 1.5, "quiz": 0.1}.get(context, 0.5)
    on, events, left = 0, [], minutes
    while left > 0:
        m = min(CHUNK_MIN, left)
        left -= m
        p_off = _clip(P["distraction_rate"] * (0.5 + (1 - learner.attention)) * ctx_w)   # never zero: even rested students drift
        if learner.off_task_streak > 0:
            p_off = max(p_off, 0.5)                                    # once scrolling, hard to stop
        if rng.random() < p_off:
            learner.off_task_streak += m
            learner.attention = _clip(learner.attention + 0.004 * m)
            if rng.random() < feed_pull / (feed_pull + PHONE_WEIGHT):
                learner.feed_minutes += m
                app = "feed"
            else:
                learner.phone_minutes += m
                app = "idle"
        else:
            learner.off_task_streak = 0
            on += m
            app = context or "idle"                                    # resting looks like idle too
        if rng.random() >= DROP_P:
            events.append({"app": app, "minutes": m})
    return (on / minutes if minutes else 1.0), events


def session_boundary(learner: LearnerState, hours: float) -> None:
    """Between sessions: p_perf resets, forgetting, attention resets, reliance decays."""
    for k in learner.p_perf:
        learner.p_perf[k] = 0.0
    for k in learner.p_know:
        learner.p_know[k] *= 2 ** (-hours / learner.half_life_h[k])
    learner.attention = 0.8
    learner.reliance = _clip(learner.reliance - 0.05 * hours / 24)
    learner.persistence = _clip(learner.persistence + 0.02 * hours / 24)


def post_test(learner: LearnerState, delay_hours: float = 0.0, n_items: int = 10, rng: random.Random | None = None) -> float:
    """Grader-run held-out exam. Unaided. Applies delay forgetting. Returns mean accuracy."""
    rng = rng or random.Random(0)
    P = learner.persona
    acc = []
    for c in learner.concepts:
        m = learner.p_know[c] * 2 ** (-delay_hours / learner.half_life_h[c])
        p = m * (1 - P["slip"]) * (1 - 0.3 * learner.reliance) + (1 - m) * P["guess"]
        acc.append(sum(rng.random() < p for _ in range(n_items)) / n_items)
    return sum(acc) / len(acc)
