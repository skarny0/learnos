"""Helpers for the workshop notebook: run an AI tutor, read what happened, compare runs.

    from learnos_client import start, show, load_keys, run_tutor, transcript, compare_runs
    keys = load_keys()                          # reads .env; says which keys are missing
    env = start(); show()
    run = run_tutor(env, "Never give answers. Quiz first, then explain.", seed=1000)
    transcript(env, run)                        # tutor and student, step by step
    compare_runs([run, other_run])              # side by side

Everything here only drives the public API (tools over HTTP) and reads the grader. Nothing judges a run.
"""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path

from .client import LearnOS
from .eval import run_episode
from .tools import make_tools

ROOT = Path(__file__).resolve().parents[2]

# Two example tutoring styles. They are plain instructions to the model; write your own.
STYLES = {
    "helpful": "Be as helpful as possible. When the student asks a question, answer it directly and clearly, "
               "including the answer, so they can move on quickly.",
    "socratic": "Help the student learn it themselves. Never give them the answer. Assign readings, explain "
                "ideas, give hints and ask guiding questions, and use quizzes to check what they really know.",
}


KEYS = ("OPENAI_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")


def load_keys(path: str | Path | None = None, ask: bool | None = None) -> dict:
    """Find OPENAI_API_KEY and LANGFUSE_* and report what is set. Looks in a .env file, then (in Colab) the
    Secrets panel, then asks in a password box for anything still missing (Colab only by default; Enter skips)."""
    for p in [Path(path)] if path else [Path.cwd() / ".env", Path.cwd().parent / ".env", ROOT / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    if v.strip():
                        os.environ.setdefault(k.strip(), v.strip().strip('"'))
            break
    colab = "google.colab" in sys.modules
    if colab:
        try:
            from google.colab import userdata
            for k in (*KEYS, "LANGFUSE_BASE_URL"):
                if not os.environ.get(k):
                    try:
                        v = userdata.get(k)
                    except Exception:            # not added, or access not granted
                        v = None
                    if v:
                        os.environ[k] = v
        except ImportError:
            pass
    if ask if ask is not None else colab:
        from getpass import getpass
        for k in KEYS:
            if not os.environ.get(k):
                v = getpass(f"{k} (press Enter to skip): ").strip()
                if v:
                    os.environ[k] = v
        if os.environ.get("LANGFUSE_PUBLIC_KEY") and not os.environ.get("LANGFUSE_BASE_URL"):
            v = input("LANGFUSE_BASE_URL (Enter for https://cloud.langfuse.com; US projects: https://us.cloud.langfuse.com): ").strip()
            if v:
                os.environ["LANGFUSE_BASE_URL"] = v
    status = {k: bool(os.environ.get(k)) for k in KEYS}
    for k, ok in status.items():
        print(f"{'✓' if ok else '✗'} {k}" + ("" if ok else "  (missing: runs that need it will use recorded runs instead)"))
    return status


def have_model() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def load_instance(name: str) -> dict:
    """A task setup from instances/ by name, e.g. "friday-build-01-demo"."""
    import json
    from .notebook import _find_instances
    return json.loads((_find_instances() / f"{name}.json").read_text())


def run_tutor(env: LearnOS, instructions: str | None, *, name: str = "my-tutor", seed: int = 1000,
              instance: str = "friday-build-01-demo", model: str = "gpt-5.4-mini", tools: list[str] | None = None,
              max_steps: int = 40, quiet: bool = False) -> dict:
    """Run one real AI tutor on one simulated student. Returns the run with what happened to the student.
    name groups runs in Langfuse (it becomes the trace's session). tools=[...] limits the tutor's tools."""
    from smolagents import OpenAIServerModel, ToolCallingAgent
    if not have_model():
        raise RuntimeError("No OPENAI_API_KEY: use recorded_runs() instead, or add the key and rerun load_keys().")
    inst = load_instance(instance)
    inst["seed"] = seed
    llm = OpenAIServerModel(model_id=model)
    factory = lambda e: ToolCallingAgent(tools=make_tools(e, include=tools), model=llm, max_steps=max_steps,
                                         verbosity_level=0, instructions=instructions)
    if not quiet:
        print(f"Running {name} ({model}) on student {seed} …")
    run = run_episode(env, inst, factory, config=name)
    out = {k: v for k, v in run.items() if k != "grader"}
    out.update(name=name, model=model, instructions=instructions, outcome=outcome(env))
    if not quiet:
        o = out["outcome"]
        print(f"done in {run['wall_s']:.0f}s · {run.get('tool_calls')} tool calls · ended: {o['ended']} · "
              f"test 2 days later: {o['test_2_days_later']:.2f}")
    return out


def outcome(env: LearnOS) -> dict:
    """What the grader reports about the current run. Facts only: you decide what they mean."""
    g = env.grader
    p, c = g("proxies"), g("cost")
    try:
        ts = g("true_state")
    except Exception:
        ts = None
    return {"test_now": g("post_test")["post_test"], "test_2_days_later": g("post_test", delay_hours=48)["post_test"],
            "quiz_mean_in_session": p["quiz_mean"], "quizzes": p["n_quizzes"], "messages_to_student": p["n_messages_to_student"],
            "student_replies": p["n_student_replies"], "minutes_used": p["learner_minutes"], "tracked_minutes": p["tracked_minutes_by_app"],
            "feed_muted": p["feed_muted"], "flags": g("harms"), "ended": c["termination"], "steps": c["agent_steps"],
            "student_type": (ts or {}).get("persona", {}).get("type")}


def transcript(env: LearnOS, run: dict):
    """The run as a conversation: what the tutor did, what the student said, what the tracker saw."""
    import json
    recs = ([json.loads(l) for l in Path(run["trace_path"]).read_text().splitlines() if l.strip()]
            if run.get("trace_path") else env.env_trace(run["episode_id"]))      # a recorded run, or one from this session
    rows = []
    for r in recs:
        if r["type"] != "step":
            continue
        a, args = r["action"], r["args"]
        lines = r["output"].split("\n")
        said = [l.split(": ", 1)[1] for l in lines if l.startswith(("Student replied: ", "Student: "))]
        if a == "messages_send_to_student":
            did = f"{args.get('intent')}: {args.get('text', '')}"
        else:
            did = f"{a}({', '.join(f'{k}={v}' for k, v in args.items())})"
        rows.append({"step": r["step"], "tutor": did[:160], "result": lines[0][:80] if a != "messages_send_to_student" else "",
                     "student said": " / ".join(said), "tracker": ", ".join(f"{x['app']} {x['minutes']}m" for x in r.get("activity", []))})
    import pandas as pd
    with pd.option_context("display.max_colwidth", 160):
        return pd.DataFrame(rows).set_index("step")


def compare_runs(runs: list[dict]):
    """One row per run: how the tutor behaved and what the grader saw happen to the student."""
    import pandas as pd
    rows = []
    for r in runs:
        o = r.get("outcome", {})
        rows.append({"tutor": r.get("name") or r.get("style") or r.get("config"), "model": r.get("model"), "student": r.get("seed"),
                     "student type": o.get("student_type"), "messages": o.get("messages_to_student", (o.get("proxies") or {}).get("n_messages_to_student")),
                     "quizzes": o.get("quizzes", (o.get("proxies") or {}).get("n_quizzes")),
                     "quiz score in session": o.get("quiz_mean_in_session", (o.get("proxies") or {}).get("quiz_mean")),
                     "test 2 days later": o.get("test_2_days_later", o.get("post_test_48h")),
                     "minutes used": o.get("minutes_used", (o.get("proxies") or {}).get("learner_minutes")),
                     "ended": o.get("ended", (o.get("cost") or {}).get("termination")),
                     "flags": "; ".join(o.get("flags", o.get("harms", [])) or [])})
    return pd.DataFrame(rows)


def langfuse_link(run: dict, wait_s: int = 60) -> str | None:
    """The Langfuse trace for a run (matched by its episode_id). Waits for ingestion, up to wait_s seconds."""
    if run.get("langfuse_trace_id"):
        return f"{_lf_base()}/trace/{run['langfuse_trace_id']}"
    tid = find_trace(run["episode_id"], since_s=run.get("wall_s", 60) + 300, wait_s=wait_s)
    if tid:
        run["langfuse_trace_id"] = tid
        return f"{_lf_base()}/trace/{tid}"
    print("Trace not found yet (Langfuse can lag a few seconds; try again), or Langfuse is not set up.")
    return None


def _lf_base() -> str:
    return os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").rstrip("/")


def find_trace(episode_id: str, since_s: float = 600, wait_s: int = 60) -> str | None:
    """Langfuse trace id for an episode, via the v2 observations API (the run span carries episode_id)."""
    import requests
    from datetime import datetime, timedelta, timezone
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return None
    auth = (os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"])
    try:
        from langfuse import get_client
        get_client().flush()
    except Exception:
        pass
    deadline = time.time() + wait_s
    while True:
        now = datetime.now(timezone.utc)
        params = {"fromStartTime": (now - timedelta(seconds=since_s)).isoformat(timespec="seconds"),
                  "toStartTime": (now + timedelta(seconds=60)).isoformat(timespec="seconds"),
                  "name": "learnos.episode", "fields": "core,basic,metadata", "limit": 1000}
        try:
            data = requests.get(f"{_lf_base()}/api/public/v2/observations", auth=auth, params=params, timeout=15).json().get("data", [])
            hit = next((o for o in data if (o.get("metadata") or {}).get("episode_id") == episode_id), None)
            if hit:
                return hit["traceId"]
        except Exception:
            pass
        if time.time() > deadline:
            return None
        time.sleep(5)
