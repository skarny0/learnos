"""Regression tests for bugs found in the Phase 0 review."""
import json, tempfile, warnings
from pathlib import Path

from test_smoke import INST, make, LearnOSEnv, Instance
from learnos_env.state import QuizResult


def test_quiz_log_is_typed_and_has_no_mood():
    env = make()
    with warnings.catch_warnings():
        warnings.simplefilter("error")                 # pydantic serializer warnings fail the test
        env.step("quiz_run", {"concept": "pomdp", "n_items": 3, "difficulty": 0.5})
        ws = env.state.workspace.model_dump()            # what the desktop payload serializes
    assert isinstance(env.state.workspace.quiz_log[0], QuizResult)
    assert "mood" not in ws["quiz_log"][0] and "asks_for_answer" not in ws["quiz_log"][0]


def test_observe_reports_done():
    env = make()
    assert env.observe()["done"] is False
    env.step("session_end", {"summary": "x"})
    obs = env.observe()
    assert obs["done"] is True and obs["termination"] == "end_session"


def test_invalid_actions_consume_budget():
    env = make()
    for _ in range(INST["budget"]["agent_steps"]):
        env.step("nope_x", {})
    assert env.state.done and env.state.termination == "step_budget"


def test_bad_args_reported_not_raised():
    env = make()
    out = env.step("files_ls", {"pth": "/course"})
    assert out["output"].startswith("Bad arguments") and out["step"] == 1


def test_calendar_overlap_uses_absolute_time():
    env = make()
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
    env = make()
    env.step("session_end", {"summary": "x"})
    recs = [json.loads(l) for l in env.trace.path.read_text().splitlines()]
    assert recs[0]["type"] == "episode_start" and recs[-1]["type"] == "episode_end"
    assert "feed_minutes" in recs[-1]["hidden"]


def _demo(minutes=90):
    import json, tempfile
    from pathlib import Path
    from learnos_env.env import LearnOSEnv
    from learnos_env.state import Instance
    d = json.load(open(Path(__file__).resolve().parents[2] / "instances" / "friday-build-01.json"))
    d.update(budget={"agent_steps": 40, "learner_minutes": minutes, "sessions": 1})
    e = LearnOSEnv(Path(tempfile.mkdtemp()), "sim"); e.reset(Instance(**d)); return e


def test_quiz_shrinks_to_the_time_left():
    e = _demo(minutes=7)
    e.step("quiz_run", {"concept": "pomdp", "n_items": 5, "difficulty": 0.5})
    q = e.state.workspace.quiz_log[-1]
    assert q.n == 2 and e.state.workspace.t == 6                      # 2 items x 3 min, not 5 items in 7 min


def test_wait_reports_the_minutes_it_actually_waited():
    e = _demo(minutes=10)
    out = e.step("session_wait", {"minutes": 30})
    assert "Waited 10 minutes" in out["output"] and e.state.workspace.t == 10


def test_message_without_concept_words_teaches_no_concept():
    e = _demo()
    assert e._resolve({"kind": "nudge", "text": "ok go"})["concept"] is None
    assert e._resolve({"kind": "explain", "text": "Your belief is a distribution over states you cannot observe."})["concept"] == "pomdp"
    assert e._substance("I think the weather is nice and hidden in the clouds today", "pomdp") == 0


def test_unknown_intent_counts_as_other():
    e = _demo()
    out = e.step("messages_send_to_student", {"text": "what do you think?", "intent": "question", "concept": ""})
    sent = [m for m in e.state.workspace.messages if m.author == "agent"][-1]
    assert sent.intent == "other" and "Sent." in out["output"]


def test_screen_shows_what_is_in_front_of_the_student():
    env = make()
    scr = env.observe()["screen"]
    assert scr["app"] == "messages"                         # they start in the chat where they asked for help
    out = env.step("reader_open_section", {"path": "/course/readings/week3/environments.md",
                                           "section": "Partial observability (POMDP)", "concept": "pomdp"})
    scr = out["observation"]["screen"]
    assert scr["app"] == env.state.workspace.student_activity[-1].app
    if scr["app"] == "reader":
        assert "Partial observability" in scr["shows"]
    text = json.dumps(scr)
    for hidden in ("p_know", "attention", "motivation", "reliance", "misinfo", "relevant"):
        assert hidden not in text
