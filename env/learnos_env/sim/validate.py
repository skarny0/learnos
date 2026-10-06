"""Behavioural validation of the simulator. Run: python -m learnos_env.sim.validate

Policies run through the real environment (LearnOSEnv: tick, activity, budgets, grader post-test),
not the dynamics alone, so the checks test what an agent and the workshop actually see.

Checks (spec §6):
  1. BKT params within pyBKT fits on ASSISTments 2009-10 (10th-90th pct). [needs pyBKT + dataset; optional]
  2. No-AI error-vs-opportunity curve RMSE < 0.05 vs empirical.                [optional]
  3. Bastani et al. (PNAS 2025). Every arm practises with quizzes; the AI arms get help first.
       give_answer: in-session ratio in [1.3, 1.7], post-test delta in [-0.25, -0.10]
       hint:        in-session ratio in [1.8, 2.6], post-test delta in [-0.05,  0.05]
     Note: the paper reports exam effects in percent (GPT Base -17%, GPT Tutor ~0); these deltas are in points.
     give_answer's -0.14 points is about -29% relative: the harm is stronger than the paper's. Kept and reported.
  4. 7-day no-review retention of a once-mastered concept in [0.45, 0.65].
  5. Sanity (design, not literature): teaching beats doing nothing; an empty "explain" teaches nothing;
     a student who is nagged enough leaves.
Prints a PASS/FAIL table. Students re-run this after any change to dynamics.
"""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path

from .dynamics import init_learner, session_boundary

INSTANCES = Path(os.environ.get("LEARNOS_INSTANCES_DIR", Path(__file__).resolve().parents[3] / "instances"))
os.environ.setdefault("LEARNOS_INSTANCES_DIR", str(INSTANCES))
from ..env import LearnOSEnv          # noqa: E402  (materials reads the env var at import)
from ..grader import GraderView       # noqa: E402
from ..state import Instance          # noqa: E402

R = "/course/readings/week3/"
SECTION = {"pomdp": (R + "environments.md", "Partial observability (POMDP)"),
           "attention": (R + "environments.md", "Attention as a hidden variable"),
           "pass_k": (R + "evaluation.md", "pass@k vs pass^k")}
ANSWER = {"pomdp": "The answer is: a belief.", "attention": "The answer is: attention.", "pass_k": "The answer is: all of them."}
HINT = {"pomdp": "What does the agent keep track of when the state is hidden and only partially observed?",
        "attention": "Think about what hidden variable decides whether you learn what you are shown. Is it focus?",
        "pass_k": "How many of the k runs have to pass, if you want reliability on every seed?"}
EXPLAIN = {"pomdp": "In a POMDP the state is hidden, so the agent keeps a belief: a distribution over states it updates from each observation.",
           "attention": "Attention is a hidden variable: material you are shown only turns into learning when you focus on it.",
           "pass_k": "pass^k counts a task as solved only if all k runs pass, so it measures reliability across every seed."}


_TMP = Path(tempfile.mkdtemp(prefix="learnos-validate-"))


def _env(seed: int, steps: int = 60, minutes: int = 400) -> LearnOSEnv:
    inst = json.loads((INSTANCES / "friday-build-01.json").read_text())
    inst.update(seed=seed, level=0, budget={"agent_steps": steps, "learner_minutes": minutes, "sessions": 1})
    env = LearnOSEnv(_TMP, "sim")
    env.reset(Instance(**inst))
    return env


def _post(env: LearnOSEnv, hours: float = 48) -> float:
    return GraderView(env.state, token_ok=True).post_test(hours)


def _quiz(env, c):
    if env.state.done:
        return None
    out = env.step("quiz_run", {"concept": c, "n_items": 3, "difficulty": 0.5})
    q = env.state.workspace.quiz_log
    return q[-1].correct / q[-1].n if q and "Quiz result" in out["output"] else None


def run_policy(policy: str, seed: int, rounds: int = 3) -> tuple[float, float]:
    """Returns (in-session quiz mean, post_test(48))."""
    env = _env(seed)
    scores = []
    for _ in range(rounds):
        for c in SECTION:
            if env.state.done:
                break
            if policy == "give_answer":
                env.step("messages_send_to_student", {"text": ANSWER[c], "intent": "give_answer", "concept": c})
            elif policy == "hint":
                env.step("messages_send_to_student", {"text": HINT[c], "intent": "hint", "concept": c})
            s = _quiz(env, c)
            if s is not None:
                scores.append(s)
    return (sum(scores) / len(scores) if scores else 0.0), _post(env)


def _mean(xs):
    return sum(xs) / len(xs)


def check_bastani(n: int = 100) -> list[tuple[str, bool, str]]:
    res = {p: [run_policy(p, s) for s in range(n)] for p in ("none", "give_answer", "hint")}
    base_in, base_post = _mean([r[0] for r in res["none"]]), _mean([r[1] for r in res["none"]])
    rows = []
    for p, lo, hi, dlo, dhi in (("give_answer", 1.3, 1.7, -0.25, -0.10), ("hint", 1.8, 2.6, -0.05, 0.05)):
        ratio = _mean([r[0] for r in res[p]]) / max(base_in, 1e-6)
        delta = _mean([r[1] for r in res[p]]) - base_post
        rows.append((f"{p}: in-session ratio {ratio:.2f} in [{lo},{hi}]", lo <= ratio <= hi, ""))
        rows.append((f"{p}: post-test delta {delta:+.2f} in [{dlo},{dhi}]", dlo <= delta <= dhi, ""))
    return rows


def check_retention() -> list[tuple[str, bool, str]]:
    L = init_learner(["c1"], 0, {"prior": 1.0})
    session_boundary(L, hours=24 * 7)
    r = L.p_know["c1"]
    return [(f"7-day retention {r:.2f} in [0.45,0.65]", 0.45 <= r <= 0.65, "")]


def _teach(seed: int, how: str) -> float:
    env = _env(seed, steps=25, minutes=90)
    for c in SECTION:
        if env.state.done:
            break
        if how == "read":
            path, sec = SECTION[c]
            env.step("reader_open_section", {"path": path, "section": sec, "concept": c})
            env.step("messages_send_to_student", {"text": EXPLAIN[c], "intent": "explain", "concept": c})
            _quiz(env, c)
        elif how == "junk_explain":
            for _ in range(2):
                env.step("messages_send_to_student", {"text": "x", "intent": "explain", "concept": c})
    if not env.state.done:
        env.step("session_end", {"summary": ""})
    return _post(env)


def check_sanity(n: int = 60) -> list[tuple[str, bool, str]]:
    nothing = _mean([_teach(s, "none") for s in range(n)])
    teach = _mean([_teach(s, "read") for s in range(n)])
    junk = _mean([_teach(s, "junk_explain") for s in range(n)])
    left = 0
    for s in range(n):
        env = _env(s, steps=25, minutes=90)
        for _ in range(20):
            if env.state.done:
                break
            env.step("messages_send_to_student", {"text": "focus!", "intent": "nudge", "concept": ""})
        left += env.state.termination == "student_left"
    return [(f"teaching beats doing nothing: post-test {teach:.2f} vs {nothing:.2f} (+0.08 or more)", teach - nothing >= 0.08, ""),
            (f"empty 'explain' teaches nothing: {junk:.2f} vs {nothing:.2f} (within 0.03)", abs(junk - nothing) <= 0.03, ""),
            (f"nagged students leave: {left}/{n} (at least half)", left >= n / 2, "")]


def all_checks() -> list[tuple[str, bool, str]]:
    return check_bastani() + check_retention() + check_sanity()


if __name__ == "__main__":
    for name, ok, note in all_checks():
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {note}")
