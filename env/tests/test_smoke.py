"""Smoke test: reset, take a few steps, grader signals exist, no reward anywhere."""
import os, json, tempfile
from pathlib import Path
import pytest

os.environ["LEARNOS_INSTANCES_DIR"] = str(Path(__file__).resolve().parents[2] / "instances")
from learnos_env.env import LearnOSEnv
from learnos_env.state import Instance
from learnos_env.grader import GraderView, Unavailable

INST = json.loads((Path(__file__).resolve().parents[2] / "instances" / "friday-build-01.json").read_text())


def make(level=1):
    env = LearnOSEnv(Path(tempfile.mkdtemp()), "sim")
    env.reset(Instance(**{**INST, "level": level}))
    return env


def test_reset_and_observe_hides_learner():
    env = make()
    obs = env.observe()
    s = json.dumps(obs)
    for hidden in ("p_know", "p_perf", "attention", "motivation", "reliance", "persistence"):
        assert hidden not in s


def test_steps_and_budget():
    env = make()
    out = env.step("files_ls", {"path": "/course"})
    assert "readings" in out["output"]
    out = env.step("messages_read_channel", {"channel": "#course"})
    assert "pass^k" in out["output"]
    out = env.step("quiz_run", {"concept": "pomdp", "n_items": 3, "difficulty": 0.5})
    assert "Quiz result" in out["output"]


def test_grader_levels():
    env = make(level=1)
    g = GraderView(env.state, token_ok=True)
    with pytest.raises(Unavailable):
        g.true_state()                     # level 1: only at episode end
    env.step("session_end", {"summary": "done"})
    assert "p_know" in g.true_state()
    assert isinstance(g.post_test(48), float)
    assert "quiz_mean" in g.proxies()


def test_no_token_no_peek():
    env = make(level=0)
    g = GraderView(env.state, token_ok=False)
    for signal in ("true_state", "proxies", "final_workspace", "transcript", "cost", "feed_audit"):
        with pytest.raises(Unavailable):
            getattr(g, signal)()
    with pytest.raises(Unavailable):
        g.post_test(48)                    # the agent must not be able to read its own outcome


def test_level2_event_fires():
    inst = json.loads((Path(__file__).resolve().parents[2] / "instances" / "friday-build-02-dynamic.json").read_text())
    env = LearnOSEnv(Path(tempfile.mkdtemp()), "sim")
    env.reset(Instance(**inst))
    env.step("session_wait", {"minutes": 30})
    assert any("2pm" in m.text for m in env.state.workspace.messages)
    assert env.state.workspace.calendar["friday"].start == 2880
