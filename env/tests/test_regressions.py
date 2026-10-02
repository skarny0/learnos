"""Regression tests for bugs found in the Phase 0 review."""
import json, tempfile, warnings
from pathlib import Path

from test_smoke import INST, make, LearnOSEnv, Instance
from learnos_env.state import QuizResult


def test_quiz_log_is_typed_and_has_no_mood():
    env = make(0)
    with warnings.catch_warnings():
        warnings.simplefilter("error")                 # pydantic serializer warnings fail the test
        env.step("quiz_run", {"concept": "pomdp", "n_items": 3, "difficulty": 0.5})
        ws = env.observe()["workspace"]
    assert isinstance(env.state.workspace.quiz_log[0], QuizResult)
    assert "mood" not in ws["quiz_log"][0] and "asks_for_answer" not in ws["quiz_log"][0]


def test_observe_reports_done():
    env = make(1)
    assert env.observe()["done"] is False
    env.step("session_end", {"summary": "x"})
    obs = env.observe()
    assert obs["done"] is True and obs["termination"] == "end_session"


def test_invalid_actions_consume_budget():
    env = make(1)
    for _ in range(INST["budget"]["agent_steps"]):
        env.step("nope_x", {})
    assert env.state.done and env.state.termination == "step_budget"


def test_bad_args_reported_not_raised():
    env = make(1)
    out = env.step("files_ls", {"pth": "/course"})
    assert out["output"].startswith("Bad arguments") and out["step"] == 1


def test_calendar_overlap_uses_absolute_time():
    env = make(0)
    env.step("session_wait", {"minutes": 60})
    env.step("session_wait", {"minutes": 10})          # t=70, lecture runs 60..150
    out = env.step("calendar_add_block", {"title": "x", "start": 0, "duration": 30, "concept": "pomdp"})
    assert "Overlaps with lecture" in out["output"]


def test_each_reset_gets_its_own_trace():
    d = Path(tempfile.mkdtemp())
    env = LearnOSEnv(d, "sim")
    for _ in range(3):
        env.reset(Instance(**INST))
    assert len(list((d / "traces").glob("*.jsonl"))) == 3


def test_trace_logs_hidden_state_and_episode_end():
    env = make(1)
    env.step("session_end", {"summary": "x"})
    recs = [json.loads(l) for l in env.trace.path.read_text().splitlines()]
    assert recs[0]["type"] == "episode_start" and recs[-1]["type"] == "episode_end"
    assert "feed_minutes" in recs[-1]["hidden"]
