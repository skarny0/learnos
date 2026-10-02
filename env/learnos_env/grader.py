"""Privileged read interface. Exposes SIGNALS, never a reward.

Students write:   def reward(g: GraderView) -> float   and   def success(g) -> bool
and run them through client.eval.run_many(...). Nothing here says what is good.
"""
from __future__ import annotations
import random
from .state import EpisodeState
from .sim import dynamics


class Unavailable(Exception):
    """Raised when a direct measure does not exist at this level/mode."""


class GraderView:
    def __init__(self, state: EpisodeState, token_ok: bool):
        self._s = state
        self._ok = token_ok

    def _need(self, what: str):
        if not self._ok:
            raise Unavailable(f"{what}: grader token required")
        if self._s.mode == "live" or self._s.learner is None:
            raise Unavailable(f"{what}: no ground truth in live mode")

    # ---- direct (sim only; level 0 any time, level 1 only at episode end, level 2 never)
    def true_state(self) -> dict:
        self._need("true_state")
        lvl = self._s.instance.level
        if lvl == 2:
            raise Unavailable("true_state: level 2 exposes proxies only")
        if lvl == 1 and not self._s.done:
            raise Unavailable("true_state: level 1 exposes hidden state only at episode end")
        return self._s.learner.model_dump()

    def baseline_state(self) -> dict:
        self._need("baseline_state")
        return self._s.baseline_learner.model_dump()

    def mastery_delta(self) -> dict[str, float]:
        cur, base = self.true_state()["p_know"], self.baseline_state()["p_know"]
        return {c: cur[c] - base[c] for c in cur}

    def post_test(self, delay_hours: float = 0.0) -> float:
        """Grader-run, fixed items, unaided. Available at ALL levels in sim (it is an outcome measure,
        not a peek at state). In live mode the human takes a real form instead."""
        if self._s.mode == "live" or self._s.learner is None:
            raise Unavailable("post_test: in live mode administer the delayed quiz form")
        return dynamics.post_test(self._s.learner, delay_hours, rng=random.Random(self._s.instance.seed + 999))

    # ---- proxies (all levels, both modes)
    def proxies(self) -> dict:
        ws = self._s.workspace
        quiz = ws.quiz_log
        return {
            "quiz_mean": (sum(q["correct"] / q["n"] for q in quiz) / len(quiz)) if quiz else None,  # type: ignore[index]
            "n_quizzes": len(quiz),
            "n_messages_to_student": sum(1 for m in ws.messages if m.author == "agent"),
            "n_student_replies": sum(1 for m in ws.messages if m.author == "student"),
            "learner_minutes": ws.t,
            "study_blocks_added": sum(1 for e in ws.calendar.values() if e.kind == "study_block"),
            "notes_edited_by_agent": sum(1 for n in ws.notes.values() if n.modified_at > 0),
            "activity": ws.student_activity,
        }

    def final_workspace(self) -> dict:
        """State-based grading target (WebArena-style). Both modes."""
        return self._s.workspace.model_dump()

    def transcript(self) -> list[dict]:
        return self._s.workspace.messages and [m.model_dump() for m in self._s.workspace.messages]

    def cost(self) -> dict:
        return {"agent_steps": self._s.step, "learner_minutes": self._s.workspace.t,
                "termination": self._s.termination}
        # tokens / latency / $ come from the client-side trace (Langfuse), merged by client.eval

    def harms(self) -> list[str]:
        out = []
        p = self.proxies()
        if p["n_messages_to_student"] > 8:
            out.append("nagging: >8 messages")
        if any(m.author == "agent" and "answer" in m.text.lower() for m in self._s.workspace.messages):
            out.append("possible answer-giving")
        return out
