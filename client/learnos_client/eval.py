"""Eval runner. Students supply reward(g) and success(g); we supply pass@k / pass^k, cost, and the
observability glue between the agent-side trace (Langfuse) and the env-side trace (env_trace).

    from learnos_client import LearnOS, make_tools, run_many, compare
    env = LearnOS(grader_token=os.environ["LEARNOS_GRADER_TOKEN"])
    def success(g):  return g("post_test", delay_hours=48)["post_test"] > 0.6
    res = run_many(env, instances, agent_factory, success, k=4, config="gpt-mini/all-tools")
    compare([res, res2])

Each run is wrapped in an OpenTelemetry span carrying Langfuse trace attributes (name, session =
config, metadata.episode_id), so with SmolagentsInstrumentor active every Langfuse trace can be
matched to its env trace: env.env_trace(run["episode_id"]).
"""
from __future__ import annotations
import time
from contextlib import contextmanager, nullcontext
from typing import Callable
from .client import LearnOS


@contextmanager
def _episode_span(instance: dict, episode_id: str, config: str):
    try:
        from opentelemetry import trace
    except ImportError:                      # no telemetry installed: run untraced
        with nullcontext(None) as s:
            yield s
        return
    attrs = {
        "langfuse.trace.name": f"{instance['instance_id']}#{instance['seed']}",
        "langfuse.session.id": config,                       # group runs by configuration
        "langfuse.trace.tags": ["learnos", instance["instance_id"], config],
        "langfuse.trace.input": instance["instruction"],
        "langfuse.trace.metadata.episode_id": episode_id,
        "langfuse.trace.metadata.instance_id": instance["instance_id"],
        "langfuse.trace.metadata.seed": instance["seed"],
        "langfuse.trace.metadata.level": instance.get("level", 1),
        "learnos.episode_id": episode_id,
    }
    with trace.get_tracer("learnos").start_as_current_span("learnos.episode", attributes=attrs) as span:
        yield span


def agent_metrics(agent) -> dict:
    """Process/operational metrics read off a smolagents agent after run()."""
    from smolagents.memory import ActionStep
    steps = [s for s in agent.memory.steps if isinstance(s, ActionStep)]
    dur = [(s.step_number, s.timing.duration or 0.0) for s in steps if s.timing]
    tok = agent.monitor.get_total_token_counts()
    return {
        "model_calls": len(steps),
        "tool_calls": sum(len(s.tool_calls or []) for s in steps),
        "tool_sequence": [tc.name for s in steps for tc in (s.tool_calls or [])],
        "step_errors": sum(1 for s in steps if s.error),
        "input_tokens": tok.input_tokens,
        "output_tokens": tok.output_tokens,
        "slowest_step": max(dur, key=lambda x: x[1]) if dur else None,   # (step_number, seconds)
    }


def task_text(instance: dict, obs: dict) -> str:
    """What the agent is given at the start: the instruction, the budget, and (at level 1) the student's screen.
    smolagents passes the model only this text and tool outputs, so this is the whole first observation."""
    out = [instance["instruction"], ""]
    b = obs.get("budget", {})
    out.append(f"Session: {obs.get('t', 0)} of {b.get('learner_minutes')} student-minutes used, "
               f"{obs.get('step', 0)} of {b.get('agent_steps')} steps used.")
    if obs.get("screen"):                                 # level 1: the tutor follows the student's screen
        out.append(f"Student's screen right now: {obs['screen']['app']}: {obs['screen']['shows']}")
        out.append("You see what is on the student's screen (updated after every action). "
                   "Anything else on their computer you have to open with the tools.")
    else:                                                 # level 0: not told what the student is doing
        out.append("You are not told what the student is doing on their computer. "
                   "Everything you learn comes from what the tools return.")
    out.append(obs.get("hint", ""))
    if obs.get("unread_messages"):
        out.append(f"Unread messages: {obs['unread_messages']}.")
    return "\n".join(out)


def run_episode(env: LearnOS, instance: dict, agent_factory: Callable, config: str = "default",
                max_steps: int | None = None) -> dict:
    first = env.reset(instance)
    episode_id = first["episode_id"]
    agent = agent_factory(env)
    t0, err = time.time(), None
    with _episode_span(instance, episode_id, config) as span:
        try:
            final = agent.run(task_text(instance, first), **({"max_steps": max_steps} if max_steps else {}))
        except Exception as e:                               # tool-format failures count as infra errors
            final, err = f"<agent error: {e}>", type(e).__name__
        if span is not None:
            span.set_attribute("langfuse.trace.output", str(final)[:2000])
    wall = time.time() - t0
    if not env.observe().get("done", False):
        env.step("session_end", {"summary": str(final)[:500]})
    try:
        metrics = agent_metrics(agent)
    except Exception:                                        # not a smolagents agent (e.g. scripted policy)
        metrics = {}
    # NOTE: `grader` reads the env's *current* episode; use it before the next reset.
    return {"episode_id": episode_id, "config": config, "instance_id": instance["instance_id"],
            "seed": instance["seed"], "final": str(final), "agent_error": err, "wall_s": wall, **metrics,
            "grader": lambda signal, **p: env.grader(signal, **p)}


def run_many(env: LearnOS, instances: list[dict], agent_factory: Callable, success: Callable, k: int = 4,
             reward: Callable | None = None, config: str = "default", repeat_seed: bool = False) -> dict:
    """k runs per instance. repeat_seed=False gives each run a new learner (seed+i), so pass^k mixes
    agent and learner variation; repeat_seed=True keeps the learner fixed (tau-bench style)."""
    rows = []
    for inst in instances:
        outs = []
        for i in range(k):
            r = run_episode(env, {**inst, "seed": inst["seed"] + (0 if repeat_seed else i)}, agent_factory, config)
            g = r.pop("grader")
            try:
                ok = bool(success(g))
            except PermissionError as e:
                ok, r["note"] = False, str(e)
            r.update(ok=ok, reward=reward(g) if reward else None, cost=g("cost"), proxies=g("proxies"))
            outs.append(r)
        rows.append({"instance_id": inst["instance_id"], "runs": outs})
    return {"config": config, "rows": rows, "pass@k": pass_at_k(rows), "pass^k": pass_pow_k(rows), "k": k}


def pass_at_k(rows):   # any of k succeed
    return sum(any(r["ok"] for r in row["runs"]) for row in rows) / max(len(rows), 1)


def pass_pow_k(rows):  # all k succeed (tau-bench)
    return sum(all(r["ok"] for r in row["runs"]) for row in rows) / max(len(rows), 1)


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def summarize(result: dict) -> dict:
    """One row of the Part 5 comparison table for a run_many() result."""
    runs = [r for row in result["rows"] for r in row["runs"]]
    return {
        "config": result["config"], "runs": len(runs),
        "success_rate": _mean([float(r["ok"]) for r in runs]),
        f"pass@{result['k']}": result["pass@k"], f"pass^{result['k']}": result["pass^k"],
        "mean_reward": _mean([r["reward"] for r in runs]),
        "mean_wall_s": _mean([r["wall_s"] for r in runs]),
        "mean_tokens": _mean([(r.get("input_tokens") or 0) + (r.get("output_tokens") or 0) for r in runs]),
        "mean_model_calls": _mean([r.get("model_calls") for r in runs]),
        "agent_error_rate": _mean([float(bool(r["agent_error"] or r.get("step_errors"))) for r in runs]),
        "mean_env_steps": _mean([r["cost"]["agent_steps"] for r in runs]),
        "mean_learner_min": _mean([r["cost"]["learner_minutes"] for r in runs]),
    }


def compare(results: list[dict]):
    """Comparison table across configurations (pandas DataFrame if available, else list of dicts)."""
    table = [summarize(r) for r in results]
    try:
        import pandas as pd
        return pd.DataFrame(table).set_index("config")
    except ImportError:
        return table


def trace_table(records: list[dict]):
    """Flatten env_trace() records to one row per agent step, for diagnosing a run next to its
    Langfuse trace. Hidden-state columns appear only if the grader revealed them."""
    rows = []
    for r in records:
        if r["type"] != "step":
            continue
        row = {"step": r["step"], "action": r["action"], "args": r["args"], "t": r["t"],
               "output": r["output"].split("\n[activity]")[0][:200],
               "activity": ", ".join(f"{a['app']} {a['minutes']}m" for a in r.get("activity", [])),
               "events": r.get("events") or ""}
        h = r.get("hidden")
        if h:
            row.update(mean_p_know=round(sum(h["p_know"].values()) / len(h["p_know"]), 3),
                       attention=round(h["attention"], 3), motivation=round(h["motivation"], 3),
                       feed_min=h.get("feed_minutes"), phone_min=h.get("phone_minutes"))
        rows.append(row)
    try:
        import pandas as pd
        return pd.DataFrame(rows).set_index("step")
    except ImportError:
        return rows
