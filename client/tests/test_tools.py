"""make_tools must produce tools smolagents accepts (it validates forward() against inputs)."""
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "env"))
os.environ.setdefault("LEARNOS_INSTANCES_DIR", str(Path(__file__).resolve().parents[2] / "instances"))
from learnos_env.apps import tool_specs                     # the real registry, no server needed
from learnos_client import make_tools
from smolagents import CodeAgent, ToolCallingAgent
from smolagents.models import Model


class FakeClient:
    def __init__(self):
        self.calls = []

    def tools(self):
        return tool_specs()

    def step(self, action, args):
        self.calls.append((action, args))
        return {"output": "ok", "done": action == "session_end"}


class NoModel(Model):
    def generate(self, *a, **k):
        raise RuntimeError("not used")


def test_agents_accept_all_tools():
    tools = make_tools(FakeClient())
    assert len(tools) == len(tool_specs())
    ToolCallingAgent(tools=tools, model=NoModel())
    CodeAgent(tools=tools, model=NoModel())


def test_positional_and_keyword_calls_reach_step():
    c = FakeClient()
    t = {x.name: x for x in make_tools(c)}
    t["files_ls"]("/course")
    t["quiz_run"](concept="pomdp", n_items=2, difficulty=0.3)
    assert c.calls == [("files_ls", {"path": "/course"}),
                       ("quiz_run", {"concept": "pomdp", "n_items": 2, "difficulty": 0.3})]
    assert t["session_end"]("bye").endswith("[episode done]")


def test_summarize_and_trace_table():
    from learnos_client import summarize, trace_table
    run = {"ok": True, "reward": 0.5, "wall_s": 2.0, "input_tokens": 100, "output_tokens": 20, "model_calls": 4,
           "agent_error": None, "step_errors": 0, "cost": {"agent_steps": 5, "learner_minutes": 30}}
    row = summarize({"config": "a", "k": 1, "pass@k": 1.0, "pass^k": 1.0, "rows": [{"runs": [run]}]})
    assert row["success_rate"] == 1.0 and row["mean_tokens"] == 120 and row["pass^1"] == 1.0
    recs = [{"type": "episode_start"},
            {"type": "step", "step": 1, "action": "session_wait", "args": {"minutes": 10}, "t": 10,
             "output": "Waited 10 minutes.\n[activity] t=0 feed 5m", "activity": [{"app": "feed", "minutes": 5}]}]
    rows = trace_table(recs)
    rows = rows.reset_index().to_dict("records") if hasattr(rows, "reset_index") else rows
    assert rows[0]["activity"] == "feed 5m" and rows[0]["output"] == "Waited 10 minutes."
    assert "attention" not in rows[0]                    # hidden columns only when revealed
