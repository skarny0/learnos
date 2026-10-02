"""Episode logic: reset / step / observe. No reward anywhere in this file."""
from __future__ import annotations
import inspect
import random
from pathlib import Path

from .state import EpisodeState, Instance, Workspace, Message, QuizResult, ActivityEvent
from .apps import REGISTRY
from .sim import dynamics, renderer
from .trace import TraceWriter
from . import materials

# which app the student is in while an action's learner-minutes pass (None = left alone)
CONTEXT = {"read": "reader", "quiz": "quiz", "wait": None,
           "explain": "messages", "hint": "messages", "give_answer": "messages", "nudge": "messages", "other": "messages"}
RECENT_ACTIVITY = 8


class LearnOSEnv:
    def __init__(self, data_dir: Path, mode: str = "sim"):
        self.data_dir = Path(data_dir)
        self.mode = mode
        self.state: EpisodeState | None = None
        self.rng = random.Random(0)
        self.trace: TraceWriter | None = None
        self.opened: set[str] = set()        # level-1 visibility set

    # ------------------------------------------------------------ lifecycle --
    def reset(self, instance: Instance) -> dict:
        self.rng = random.Random(instance.seed)
        ws: Workspace = materials.load(instance.materials_pack, instance)
        learner = None
        if self.mode == "sim":
            learner = dynamics.init_learner(instance.concepts, instance.seed, instance.learner_profile)
        self.state = EpisodeState(instance=instance, workspace=ws, learner=learner,
                                  baseline_learner=learner.model_copy(deep=True) if learner else None,
                                  mode=self.mode)
        self.opened = set()
        if self.trace:
            self.trace.close()
        self.trace = TraceWriter(self.data_dir / "traces", instance.instance_id, instance.seed)
        self.trace.episode_start(instance, hidden=learner)
        return self.observe()

    def step(self, action: str, args: dict) -> dict:
        s = self.state
        assert s and not s.done, "call reset() first / episode is done"
        app, _, name = action.partition("_")
        if app not in REGISTRY or name not in REGISTRY[app]:
            return self._invalid(action, args, f"Unknown action: {action}")
        fn = REGISTRY[app][name].fn
        try:
            inspect.signature(fn).bind(s, **args)
        except TypeError as e:
            return self._invalid(action, args, f"Bad arguments: {e}")
        result = fn(s, **args)

        # learner side
        obs_extra: dict = {}
        activity: list[ActivityEvent] = []
        effect = result.learner_effect
        if s.mode == "sim" and s.learner and (effect or result.learner_minutes):
            if result.learner_minutes:
                on, raw = dynamics.tick(s.learner, result.learner_minutes, CONTEXT.get(effect.get("kind")),
                                        self._feed_pull(), self.rng)
                activity = self._stamp(raw)
                if effect:
                    effect = {**effect, "on_task": on}
            if effect:
                obs_extra = dynamics.apply(s.learner, effect, self.rng)
            if effect.get("kind") == "quiz":
                result.output = renderer.quiz_feedback(obs_extra)
                s.workspace.quiz_log.append(QuizResult(concept=effect["concept"], n=obs_extra["n"],
                                                       correct=obs_extra["correct"], difficulty=effect["difficulty"],
                                                       t=s.workspace.t, aided=obs_extra["aided"]))
            elif effect.get("kind") in ("explain", "hint", "give_answer", "nudge", "other"):
                r = renderer.reply(obs_extra, self.rng)
                if r:
                    s.workspace.messages.append(Message(id=f"m{len(s.workspace.messages)+1}", channel="dm:student",
                                                        author="student", text=r, t=s.workspace.t))
                    result.output += f"\nStudent replied: {r}"
        # live mode: learner_effect is dispatched to the real UI (notification / quiz form) by server.py;
        # activity arrives via POST /live/activity instead of dynamics.tick.

        s.workspace.student_activity.extend(activity)
        if activity:
            result.output += "\n[activity] " + "; ".join(f"t={a.t} {a.app} {a.minutes}m" for a in activity)

        # clock + budget
        s.workspace.t += result.learner_minutes
        self.opened.update(result.opened)
        self._apply_scheduled_events()
        self._count_step()
        return self._finish_step(action, args, result.output, obs_extra, result.events)

    def _invalid(self, action, args, msg) -> dict:
        """Malformed calls still cost an agent step, so a looping agent exhausts its budget."""
        self._count_step()
        return self._finish_step(action, args, msg, {})

    def _count_step(self) -> None:
        s = self.state
        s.step += 1
        b = s.instance.budget
        if s.done:
            return
        if s.step >= b.agent_steps:
            s.done, s.termination = True, "step_budget"
        elif s.workspace.t >= b.learner_minutes:
            s.done, s.termination = True, "learner_minutes"

    def _feed_pull(self) -> float:
        """Share of the published feed the agent has not muted (input to dynamics.tick)."""
        ws = self.state.workspace
        posts = [p for p in ws.feed if p.t <= ws.t]
        if not posts or "all" in ws.feed_muted:
            return 0.0
        return sum(p.source not in ws.feed_muted for p in posts) / len(posts)

    def _stamp(self, raw: list[dict]) -> list[ActivityEvent]:
        t, out = self.state.workspace.t, []
        for e in raw:
            out.append(ActivityEvent(t=t, app=e["app"], minutes=e["minutes"]))
            t += e["minutes"]
        return out

    def _finish_step(self, action, args, output, obs_extra, events=None) -> dict:
        s = self.state
        self.trace.step(step=s.step, action=action, args=args, output=output, t=s.workspace.t,
                        hidden=s.learner, events=events or [])
        if s.done:
            self.trace.episode_end(s.termination, hidden=s.learner)
        return {"output": output, "observation": self.observe(), "done": s.done, "step": s.step}

    # ----------------------------------------------------------- observation --
    def observe(self) -> dict:
        """Serialize Workspace filtered by level. Never includes LearnerState.
        The activity stream (tracker reports, a proxy) is included at every level."""
        s = self.state
        ws, lvl = s.workspace, s.instance.level
        base = {"t": ws.t, "step": s.step, "done": s.done, "termination": s.termination,
                "budget": s.instance.budget.model_dump(), "instruction": s.instance.instruction,
                "recent_activity": [a.model_dump() for a in ws.student_activity[-RECENT_ACTIVITY:]]}
        if lvl == 0:
            return {**base, "workspace": ws.model_dump()}
        # level 1/2: only what has been opened + unread counts
        unread = sum(1 for m in ws.messages if not m.read and m.author != "agent")
        return {**base, "open_windows": sorted(self.opened), "unread_messages": unread,
                "hint": "Use files_ls, messages_read_channel, calendar_list, notes_list, browser_visit, feed_scroll to look around."}

    # --------------------------------------------------------------- events --
    def _apply_scheduled_events(self) -> None:
        """Level 2: world changes mid-episode (message arrives, deadline moves, note edited, page breaks)."""
        s = self.state
        if s.instance.level < 2:
            return
        for ev in s.instance.events:
            if ev.get("fired") or ev["t"] > s.workspace.t:
                continue
            ev["fired"] = True
            materials.apply_event(s.workspace, ev)
            self.trace.event(ev)
