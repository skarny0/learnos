"""Behavioural validation of the simulator. Run: python -m learnos_env.sim.validate

Checks (spec §6):
  1. BKT params within pyBKT fits on ASSISTments 2009-10 (10th-90th pct). [needs pyBKT + dataset; optional]
  2. No-AI error-vs-opportunity curve RMSE < 0.05 vs empirical.                [optional]
  3. Fixed policies reproduce Bastani et al. (PNAS 2025):
       give_answer-always: in-session ratio in [1.3, 1.7], post-test delta in [-0.25, -0.10]
       hint-only:          in-session ratio in [1.8, 2.6], post-test delta in [-0.05,  0.05]
  4. 7-day no-review retention of a once-mastered concept in [0.45, 0.65].
Prints a PASS/FAIL table. Students re-run this after any change to dynamics.
"""
from __future__ import annotations
import random
from .dynamics import init_learner, apply, post_test, session_boundary

CONCEPTS = ["c1", "c2", "c3"]


def _run_policy(policy: str, seed: int, steps: int = 12) -> tuple[float, float]:
    rng = random.Random(seed)
    L = init_learner(CONCEPTS, seed)
    base = post_test(L, rng=random.Random(seed))
    in_session = []
    for i in range(steps):
        c = CONCEPTS[i % 3]
        if policy == "give_answer":
            apply(L, {"kind": "give_answer", "concept": c}, rng)
        elif policy == "hint":
            apply(L, {"kind": "hint", "concept": c}, rng)
        elif policy == "none":
            apply(L, {"kind": "read", "concept": c, "minutes": 5}, rng)
        o = apply(L, {"kind": "quiz", "concept": c, "n": 3, "difficulty": 0.5}, rng)
        in_session.append(o["correct"] / o["n"])
    session_boundary(L, hours=24 * 7)
    return sum(in_session) / len(in_session), post_test(L, rng=random.Random(seed)) - base


def check_bastani(n: int = 200) -> list[tuple[str, bool, str]]:
    res = {p: [_run_policy(p, s) for s in range(n)] for p in ("none", "give_answer", "hint")}
    mean = lambda xs: sum(xs) / len(xs)
    base_in = mean([r[0] for r in res["none"]])
    rows = []
    for p, lo, hi, dlo, dhi in (("give_answer", 1.3, 1.7, -0.25, -0.10), ("hint", 1.8, 2.6, -0.05, 0.05)):
        ratio = mean([r[0] for r in res[p]]) / max(base_in, 1e-6)
        delta = mean([r[1] for r in res[p]]) - mean([r[1] for r in res["none"]])
        rows.append((f"{p}: in-session ratio {ratio:.2f} in [{lo},{hi}]", lo <= ratio <= hi, ""))
        rows.append((f"{p}: post-test delta {delta:+.2f} in [{dlo},{dhi}]", dlo <= delta <= dhi, ""))
    return rows


def check_retention() -> list[tuple[str, bool, str]]:
    L = init_learner(["c1"], 0, {"prior": 1.0})
    session_boundary(L, hours=24 * 7)
    r = L.p_know["c1"]
    return [(f"7-day retention {r:.2f} in [0.45,0.65]", 0.45 <= r <= 0.65, "")]


if __name__ == "__main__":
    rows = check_bastani() + check_retention()
    for name, ok, note in rows:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {note}")
    # NOTE: parameters are a first guess; expect FAILs until dynamics are tuned. That is the point.
