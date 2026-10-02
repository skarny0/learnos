"""Eval runner. Students supply reward(g) and success(g); we supply pass@k / pass^k and cost.

    from learnos_client import LearnOS, make_tools, run_many
    env = LearnOS(grader_token=os.environ["LEARNOS_GRADER_TOKEN"])
    def success(g):  return g("post_test", delay_hours=48)["post_test"] > 0.6
    run_many(env, instances, agent_factory, success, k=4)
"""
from __future__ import annotations
import time
from typing import Callable
from .client import LearnOS


def run_episode(env: LearnOS, instance: dict, agent_factory: Callable, max_steps: int | None = None) -> dict:
    env.reset(instance)
    agent = agent_factory(env)
    t0 = time.time()
    try:
        final = agent.run(instance["instruction"], max_steps=max_steps) if max_steps else agent.run(instance["instruction"])
    except Exception as e:                                   # tool-format failures count as infra errors
        final = f"<agent error: {e}>"
    obs = env.observe()
    if not obs.get("done", False):
        env.step("session_end", {"summary": str(final)[:500]})
    return {"instance_id": instance["instance_id"], "seed": instance["seed"], "final": str(final),
            "wall_s": time.time() - t0, "grader": lambda signal, **p: env.grader(signal, **p)}


def run_many(env: LearnOS, instances: list[dict], agent_factory: Callable, success: Callable, k: int = 4,
             reward: Callable | None = None) -> dict:
    rows = []
    for inst in instances:
        outs = []
        for i in range(k):
            r = run_episode(env, {**inst, "seed": inst["seed"] + i}, agent_factory)
            g = r["grader"]
            try:
                ok = bool(success(g))
            except PermissionError as e:
                ok, r["note"] = False, str(e)
            rw = reward(g) if reward else None
            outs.append({"ok": ok, "reward": rw, "cost": g("cost"), "proxies": g("proxies"), "wall_s": r["wall_s"]})
        rows.append({"instance_id": inst["instance_id"], "runs": outs})
    return {"rows": rows, "pass@k": pass_at_k(rows), "pass^k": pass_pow_k(rows), "k": k}


def pass_at_k(rows):   # any of k succeed
    return sum(any(r["ok"] for r in row["runs"]) for row in rows) / max(len(rows), 1)


def pass_pow_k(rows):  # all k succeed (tau-bench)
    return sum(all(r["ok"] for r in row["runs"]) for row in rows) / max(len(rows), 1)
