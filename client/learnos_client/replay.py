"""Replay a recorded run on the LearnOS desktop.

    from learnos_client import replay, recorded_runs
    runs = recorded_runs()                      # the runs saved in data/reference/, newest first
    replay(env, runs[0], delay=1.5)             # plays it step by step; watch it with show()

The environment is seeded, so sending the same tool calls to the same student reproduces the run
exactly: same student replies, same quiz results, same tracker events, same grader numbers. Each step's
output is compared with the recording; if the simulator has changed since the run was recorded,
replay says where the two first differ.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from .client import LearnOS

REFERENCE = Path(__file__).resolve().parents[2] / "data" / "reference"


def recorded_runs(folder: str | Path | None = None, instance: str | None = None, style: str | None = None) -> list[dict]:
    """Summaries of recorded runs (newest first), each with its trace file under "trace_path"."""
    folder = Path(folder) if folder else REFERENCE
    out = []
    for p in sorted(folder.glob("*.summary.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        s = json.loads(p.read_text())
        trace = p.with_name(p.name.replace(".summary.json", ".jsonl"))
        if not trace.exists():
            continue
        if instance and s.get("instance_id") != instance:
            continue
        if style and s.get("style") != style:
            continue
        out.append({**s, "trace_path": str(trace)})
    return out


def replay(env: LearnOS, run: dict | str | Path, delay: float = 1.5, verbose: bool = True) -> dict:
    """Re-send a recorded run's tool calls, one every `delay` seconds. Returns {episode_id, matched, first_diff}.
    `run` is an entry from recorded_runs(), or a path to a recorded .jsonl trace."""
    path = Path(run["trace_path"] if isinstance(run, dict) else run)
    recs = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    start = next(r for r in recs if r["type"] == "episode_start")
    inst = {**start["instance"], "events": [{k: v for k, v in e.items() if k != "fired"} for e in start["instance"].get("events", [])]}
    steps = [r for r in recs if r["type"] == "step"]
    episode_id = env.reset(inst)["episode_id"]
    first_diff = None
    for r in steps:
        time.sleep(delay)
        out = env.step(r["action"], r["args"])
        if first_diff is None and out["output"] != r["output"]:
            first_diff = {"step": r["step"], "action": r["action"], "recorded": r["output"][:200], "now": out["output"][:200]}
        if verbose:
            line = out["output"].splitlines()[0][:80] if out["output"] else ""
            print(f"#{r['step']:>2} {r['action']:<26} {line}")
        if out.get("done"):
            break
    if verbose and first_diff:
        print(f"\nNote: step {first_diff['step']} differs from the recording (the simulator changed since it was recorded).")
    return {"episode_id": episode_id, "matched": first_diff is None, "first_diff": first_diff}
