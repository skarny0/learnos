"""Hidden-learner dynamics. All numbers, all seeded. See spec §5 for parameter rationale.

Learning is an expected-value update, p_know += gain * (1 - p_know), where gain depends on the
action, the student's attention and motivation, and how much of the action they were on task for.
Practice (an unaided quiz) teaches too, so a tutor that does the work for the student skips learning.

Persona defaults: slip = 0.10, guess = 0.20 (BKT range on ASSISTments 2009-10).
"""
from __future__ import annotations
import random
from ..state import LearnerState

DEFAULT_PERSONA = dict(learn_rate=0.30, slip=0.10, guess=0.20, fatigue_rate=0.02, distraction_rate=0.3)

HALF_LIFE_H = 192.0    # memory half-life of a fresh concept (7-day retention ~0.55)
HALF_LIFE_MAX = 4.0    # retrieval practice can stretch it to at most 4x
# gain per action, as a multiple of persona learn_rate
GAIN = {"read": 1.0, "explain": 0.8, "hint": 0.6, "give_answer": 0.05}
PRACTICE_GAIN = 0.25   # per unaided quiz item, as a multiple of learn_rate
RELIANCE_PENALTY = 0.5 # at the post-test, mastery is used at (1 - this * reliance): gives up without help
LEAVE_BELOW = 0.2      # motivation below this: the student quits the session
GIVE_PERF = 0.75       # in-session recognition right after being given the answer
HINT_PERF = 1.0        # recognition added per hint
NAG_LIMIT = 3.0        # more recent messages than this and each new one annoys


# Student types: trait ranges a seed draws from. A profile with "type": "<name>" or "random" uses them;
# any trait the profile sets explicitly wins over the draw. Ranges are first guesses, not fitted to data.
STUDENT_TYPES = {
    "focused":          dict(learn_rate=(0.30, 0.40), distraction_rate=(0.08, 0.18), prior=(0.20, 0.35),
                             persistence=(0.75, 0.90), motivation=(0.65, 0.85)),
    "distractible":     dict(learn_rate=(0.25, 0.35), distraction_rate=(0.50, 0.70), prior=(0.15, 0.30),
                             attention=(0.45, 0.65)),
    "answer_seeking":   dict(learn_rate=(0.25, 0.35), distraction_rate=(0.25, 0.40), prior=(0.15, 0.30),
                             reliance=(0.30, 0.50), persistence=(0.30, 0.50)),
    "strong_but_bored": dict(learn_rate=(0.30, 0.40), distraction_rate=(0.30, 0.45), prior=(0.55, 0.75),
                             motivation=(0.40, 0.55)),
    "slow_and_steady":  dict(learn_rate=(0.15, 0.22), distraction_rate=(0.10, 0.20), prior=(0.10, 0.25),
                             persistence=(0.80, 0.95)),
}
_STATE_TRAITS = ("prior", "reliance", "persistence", "motivation", "attention")


def draw_traits(seed: int, kind: str) -> dict:
    """Pick a student type (if kind == "random") and draw each trait uniformly from its range."""
    rng = random.Random(f"type:{seed}")
    name = rng.choice(sorted(STUDENT_TYPES)) if kind == "random" else kind
    return {"type": name, **{k: rng.uniform(*r) for k, r in STUDENT_TYPES[name].items()}}


# ---------------------------------------------------------------- plugin rules --
# Participants can add their own student rules without editing this file. A rule is a plain function
# that runs here, inside the dynamics, after the built-in rules for every event:
#     def rule(learner, event, rng): ...      # nudge numbers in learner.extra / p_know / attention / ...
# `event` is the action's effect ({"kind": "read" | "explain" | "hint" | "give_answer" | "nudge" | "quiz" |
# "wait" | "mute" | "see_post", "concept", ...}; a quiz event also carries "correct" and "n", a see_post
# event carries "tag" and "concept"). `init(learner, rng)` returns the new traits' starting values.
# Rules must stay numeric and use only `rng` for chance, so runs stay seeded and repeatable.
RULES: list[tuple[str, object, object]] = []


def add_rule(name: str, rule, init=None) -> None:
    """Register a student rule (replaces an earlier rule with the same name)."""
    remove_rule(name)
    RULES.append((name, rule, init))


def remove_rule(name: str | None = None) -> None:
    """Remove one rule by name, or all of them."""
    RULES[:] = [r for r in RULES if name is not None and r[0] != name]


def _run_rules(learner: LearnerState, event: dict, rng: random.Random) -> None:
    for _, rule, _ in RULES:
        rule(learner, event, rng)


def init_learner(concepts: list[str], seed: int, profile: dict | None = None) -> LearnerState:
    rng = random.Random(seed)
    profile = dict(profile or {})
    kind = profile.pop("type", None)
    drawn = draw_traits(seed, kind) if kind else {}
    persona = {**DEFAULT_PERSONA, **drawn, **profile}
    st = {k: persona.pop(k) for k in _STATE_TRAITS if k in persona}
    prior = st.get("prior")
    L = LearnerState(
        concepts=concepts,
        p_know={c: (prior if prior is not None else rng.betavariate(1, 4)) for c in concepts},
        p_perf={c: 0.0 for c in concepts},
        half_life_h={c: HALF_LIFE_H for c in concepts},
        attention=st.get("attention", rng.betavariate(5, 2)),
        motivation=st.get("motivation", rng.betavariate(4, 2)),
        reliance=st.get("reliance", 0.0),
        persistence=st.get("persistence", rng.betavariate(6, 2)),
        persona=persona,                                             # includes "type" when drawn (grader-only)
    )
    rrng = random.Random(f"rules:{seed}")                            # separate stream: adding a rule never shifts the others
    for _, _, init in RULES:
        if init:
            L.extra.update(init(L, rrng))
    return L


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _learn(L: LearnerState, c: str | None, gain: float) -> None:
    if c in L.p_know and gain > 0:
        L.p_know[c] = _clip(L.p_know[c] + gain * (1 - L.p_know[c]))


def _engaged(L: LearnerState) -> float:
    """How much a bored or fed-up student still takes in."""
    return L.attention * (0.4 + 0.6 * L.motivation)


def apply(learner: LearnerState, effect: dict, rng: random.Random) -> dict:
    """Mutate learner in place according to an agent action's learner_effect.
    Returns an observation dict (what the agent gets to see), e.g. quiz result or reply bin.

    effect keys: kind, concept, on_task (share of the action the student was on task, from tick),
    quality (0-1, how much substance a message had for its concept; set by env from the text)."""
    L, P = learner, learner.persona
    kind = effect.get("kind")
    c = effect.get("concept") or None
    on = effect.get("on_task", 1.0)
    q = effect.get("quality", 1.0)
    noise = rng.uniform(0.7, 1.3)                                    # same action, slightly different uptake
    obs: dict = {}

    if kind in ("explain", "hint", "give_answer", "nudge", "other"):
        L.nag = L.nag * 0.7 + 1                                      # recent-message pressure
        if L.nag > NAG_LIMIT:
            L.motivation = _clip(L.motivation - 0.05)                # too many messages

    if kind == "read":
        _learn(L, c, GAIN["read"] * P["learn_rate"] * _engaged(L) * on * noise)
        L.attention = _clip(L.attention - P["fatigue_rate"] * effect.get("minutes", 5) / 3)

    elif kind == "explain":
        _learn(L, c, GAIN["explain"] * P["learn_rate"] * _engaged(L) * on * q * noise)
        if c in L.p_know and L.p_know[c] > 0.9:
            L.motivation = _clip(L.motivation - 0.05)                # boredom: already knows it

    elif kind == "hint":
        _learn(L, c, GAIN["hint"] * P["learn_rate"] * _engaged(L) * on * q * noise)
        if c in L.p_perf:
            L.p_perf[c] = _clip(L.p_perf[c] + HINT_PERF * on)
        L.reliance = _clip(L.reliance + 0.02 * on)

    elif kind == "give_answer":                                      # the Bastani "crutch"
        _learn(L, c, GAIN["give_answer"] * P["learn_rate"] * _engaged(L) * on * noise)
        if c in L.p_perf:
            L.p_perf[c] = max(L.p_perf[c], GIVE_PERF * on)                # copied answers are half-understood
        L.reliance = _clip(L.reliance + 0.08 * on)
        L.persistence = _clip(L.persistence - 0.03 * on)

    elif kind == "nudge":
        if L.attention < 0.5:
            L.attention = _clip(L.attention + 0.2)
        else:
            L.motivation = _clip(L.motivation - 0.05)                # annoyance: they were working

    elif kind == "quiz":
        n, d = effect["n"], effect["difficulty"]
        aided = L.p_perf.get(c, 0.0) > 0.1
        m = max(L.p_know.get(c, 0.0), L.p_perf.get(c, 0.0)) if aided else L.p_know.get(c, 0.0)
        m = _clip(m - 0.4 * (d - 0.5))                               # difficulty shifts effective mastery
        m *= 0.6 + 0.4 * L.attention                                 # attention confound (on mastery, not guessing)
        p = m * (1 - P["slip"]) + (1 - m) * P["guess"]
        correct = sum(rng.random() < p for _ in range(n))
        if c in L.p_know:
            if not aided:                                            # practice: working it out teaches
                _learn(L, c, PRACTICE_GAIN * P["learn_rate"] * n * _engaged(L) * on)
            base = HALF_LIFE_H
            if correct / n >= 0.67 and not aided and d >= 0.4:       # retrieval practice, on real items only
                L.half_life_h[c] = min(L.half_life_h[c] * 1.5, base * HALF_LIFE_MAX)
                L.motivation = _clip(L.motivation + 0.05)
            elif correct / n < 0.34:
                L.half_life_h[c] = max(L.half_life_h[c] * 0.9, base / 2)
                L.motivation = _clip(L.motivation - 0.08 * (1 - L.persistence))
            L.p_perf[c] *= 0.5                                       # borrowed help wears off
        L.attention = _clip(L.attention - 0.01 * n)
        obs = {"correct": correct, "n": n, "aided": aided}

    elif kind == "wait":
        mins = effect.get("minutes", 15)
        L.attention = _clip(L.attention + 0.01 * mins * (0.3 + 0.7 * on))   # scrolling rests you less than resting
        for k in L.p_know:
            L.p_know[k] *= 2 ** (-(mins / 60) / L.half_life_h[k])
        L.motivation = _clip(L.motivation + 0.1 * (0.6 - L.motivation))
        L.nag *= 0.5

    elif kind == "mute":                                             # autonomy cost of being policed
        L.motivation = _clip(L.motivation - (0.08 if effect.get("scope") == "all" else 0.03))

    if RULES:
        _run_rules(L, {**effect, **({"correct": obs["correct"], "n": obs["n"]} if kind == "quiz" else {})}, rng)

    # motivation bin for the renderer
    obs["mood"] = "frustrated" if L.motivation < 0.35 else ("engaged" if L.motivation > 0.7 else "neutral")
    obs["asks_for_answer"] = rng.random() < 0.6 * L.reliance * (1 - L.persistence)
    return obs


def initiate(learner: LearnerState, concept: str | None, on_task: float, rng: random.Random) -> str | None:
    """Does the student start a conversation on their own? Called after learner time passes.
    Returns 'ask_answer', 'confused', or None. Only while they are (mostly) on task and still struggling."""
    if on_task < 0.5 or concept not in learner.p_know or learner.p_know[concept] > 0.6:
        return None
    if rng.random() < 0.05 + 0.7 * learner.reliance * (1 - learner.persistence):
        return "ask_answer"
    if rng.random() < 0.15 * (1 - learner.p_know[concept]):
        return "confused"
    return None


def wants_to_leave(learner: LearnerState) -> bool:
    return learner.motivation < LEAVE_BELOW


CHUNK_MIN = 5          # tracker resolution
PHONE_WEIGHT = 0.3     # pull of the (untracked) phone relative to a fully unmuted feed
DROP_P = 0.05          # tracker misses a chunk


def tick(learner: LearnerState, minutes: int, context: str | None, feed_pull: float,
         rng: random.Random, posts: list[dict] | None = None) -> tuple[float, list[dict]]:
    """The student's own behaviour while `minutes` of learner time pass.

    context: the app the agent put the student in ("reader", "messages", "quiz"), or None
    when the student is left alone (session_wait). feed_pull in [0,1]: share of the feed
    that is not muted (computed by env from the workspace). posts: published, unmuted posts
    as {id, tag, concept}; the student may read one per chunk spent on the feed.

    Per 5-minute chunk the student is on task or drifts, w.p. rising with distraction_rate,
    falling with attention, and lower when there is less to scroll (muting helps, partly);
    drifting is sticky. Drift goes to the feed (tracked) or the phone (off-screen, reported as
    'idle'), so muting the feed partly displaces distraction to where the tracker cannot see it.

    Returns (on_task_fraction, tracker events). Events carry no hidden numbers.
    """
    P = learner.persona
    ctx_w = {None: 1.5, "quiz": 0.1}.get(context, 0.5)
    pull = (feed_pull + PHONE_WEIGHT) / (1 + PHONE_WEIGHT)          # 1 with a full feed, ~0.23 with all muted
    on, events, left = 0, [], minutes
    while left > 0:
        m = min(CHUNK_MIN, left)
        left -= m
        p_off = _clip(P["distraction_rate"] * (0.5 + (1 - learner.attention)) * ctx_w * (0.5 + 0.5 * pull))
        if learner.off_task_streak > 0:
            p_off = max(p_off, 0.5)                                    # once scrolling, hard to stop
        if rng.random() < p_off:
            learner.off_task_streak += m
            learner.attention = _clip(learner.attention + 0.004 * m)
            if rng.random() < feed_pull / (feed_pull + PHONE_WEIGHT):
                learner.feed_minutes += m
                app = "feed"
                _see_post(learner, posts or [], rng)
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


def _see_post(learner: LearnerState, posts: list[dict], rng: random.Random) -> None:
    """Scrolling the feed, the student reads one post they have not seen. A useful tip teaches a
    little; a wrong claim undoes a little. Noise does nothing."""
    unseen = [p for p in posts if p["id"] not in learner.seen_posts]
    if not unseen:
        return
    p = rng.choice(unseen)
    learner.seen_posts.append(p["id"])
    c = p.get("concept")
    if RULES:
        _run_rules(learner, {"kind": "see_post", "tag": p["tag"], "concept": c}, rng)
    if c in learner.p_know:
        if p["tag"] == "relevant":
            _learn(learner, c, 0.5 * learner.persona["learn_rate"])
        elif p["tag"] == "misinfo":
            learner.p_know[c] = _clip(learner.p_know[c] * 0.85)


def session_boundary(learner: LearnerState, hours: float) -> None:
    """Between sessions: p_perf resets, forgetting, attention resets, reliance decays."""
    for k in learner.p_perf:
        learner.p_perf[k] = 0.0
    for k in learner.p_know:
        learner.p_know[k] *= 2 ** (-hours / learner.half_life_h[k])
    learner.attention = 0.8
    learner.reliance = _clip(learner.reliance - 0.05 * hours / 24)
    learner.persistence = _clip(learner.persistence + 0.02 * hours / 24)


def post_test(learner: LearnerState, delay_hours: float = 0.0, n_items: int = 40, rng: random.Random | None = None) -> float:
    """Grader-run held-out exam. Unaided. Applies delay forgetting (and the decay of reliance over
    the same delay). Returns mean accuracy."""
    rng = rng or random.Random(0)
    P = learner.persona
    reliance = _clip(learner.reliance - 0.05 * delay_hours / 24)
    acc = []
    for c in learner.concepts:
        m = learner.p_know[c] * 2 ** (-delay_hours / learner.half_life_h[c])
        m *= 1 - RELIANCE_PENALTY * reliance                       # dependent students give up on hard items
        p = m * (1 - P["slip"]) + (1 - m) * P["guess"]
        acc.append(sum(rng.random() < p for _ in range(n_items)) / n_items)
    return sum(acc) / len(acc)
