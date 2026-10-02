"""episode_id links client traces to the env trace; env_trace follows the same gating as true_state."""
import json
from test_smoke import make, GraderView
from learnos_env.grader import Unavailable
import pytest


def grader(env, ok=True):
    return GraderView(env.state, token_ok=ok, trace_path=env.trace.path)


def test_episode_id_in_observation_and_trace():
    env = make(1)
    eid = env.observe()["episode_id"]
    assert env.trace.path.stem == eid
    assert json.loads(env.trace.path.read_text().splitlines()[0])["episode_id"] == eid


def test_env_trace_hides_hidden_until_level1_end():
    env = make(1)
    env.step("files_ls", {"path": "/course"})
    recs = grader(env).env_trace()
    assert [r["type"] for r in recs] == ["episode_start", "step"]
    assert all("hidden" not in r for r in recs)
    env.step("session_end", {"summary": "x"})
    recs = grader(env).env_trace()
    assert recs[-1]["type"] == "episode_end" and "p_know" in recs[-1]["hidden"]


def test_env_trace_never_reveals_at_level2():
    env = make(2)
    env.step("session_end", {"summary": "x"})
    assert all("hidden" not in r for r in grader(env).env_trace())


def test_env_trace_needs_token():
    env = make(0)
    with pytest.raises(Unavailable):
        grader(env, ok=False).env_trace()


def test_env_trace_of_a_past_episode():
    env = make(0)
    old = env.observe()["episode_id"]
    env.step("session_wait", {"minutes": 20})
    env.reset(env.state.instance)                      # a new episode
    recs = grader(env).env_trace(old)
    assert recs[0]["episode_id"] == old
    assert recs[1]["activity"] and "hidden" in recs[1]  # level 0: structured activity + hidden state
    with pytest.raises(Unavailable):
        grader(env).env_trace("../../etc/passwd")
