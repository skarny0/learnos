"""Episode logic: reset / step / observe. No reward anywhere in this file."""
from __future__ import annotations
import json
import random
from pathlib import Path

from .state import EpisodeState, Instance, Workspace, Message
from .apps import REGISTRY
from .sim import dynamics, renderer
from .trace import TraceWriter
from . import materials


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
        self.trace = TraceWriter(self.data_dir / "traces", instance.instance_id, instance.seed)
        self.trace.episode_start(instance, hidden=learner)
        return self.observe()

    def step(self, action: str, args: dict) -> dict:
        s = self.state
        assert s and not s.done, "call reset() first / episode is done"
        app, _, name = action.partition("_")
        if app not in REGISTRY or name not in REGISTRY[app]:
            return self._finish_step(action, args, f"Unknown action: {action}", {})
        try:
            result = REGISTRY[app][name].fn(s, **args)
        except TypeError as e:
            return self._finish_step(action, args, f"Bad arguments: {e}", {})

        # learner side
        obs_extra: dict = {}
        if result.learner_effect and s.mode == "sim" and s.learner:
            obs_extra = dynamics.apply(s.learner, result.learner_effect, self.rng)
            if result.learner_effect.get("kind") == "quiz":
                result.output = renderer.quiz_feedback(obs_extra)
                s.workspace.quiz_log.append({**result.learner_effect, **obs_extra, "t": s.workspace.t})  # type: ignore[arg-type]
            elif result.learner_effect.get("kind") in ("explain", "hint", "give_answer", "nudge", "other"):
                r = renderer.reply(obs_extra, self.rng)
                if r:
                    s.workspace.messages.append(Message(id=f"m{len(s.workspace.messages)+1}", channel="dm:student",
                                                        author="student", text=r, t=s.workspace.t))
                    result.output += f"\nStudent replied: {r}"
        # live mode: learner_effect is dispatched to the real UI (notification / quiz form) by server.py

        # clock + budget
        s.workspace.t += result.learner_minutes
        s.step += 1
        self.opened.update(result.opened)
        self._apply_scheduled_events()
        b = s.instance.budget
        if s.step >= b.agent_steps:
            s.done, s.termination = True, "step_budget"
        elif s.workspace.t >= b.learner_minutes:
            s.done, s.termination = True, "learner_minutes"

        return self._finish_step(action, args, result.output, obs_extra, result.events)

    def _finish_step(self, action, args, output, obs_extra, events=None) -> dict:
        s = self.state
        self.trace.step(step=s.step, action=action, args=args, output=output, t=s.workspace.t,
                        hidden=s.learner, events=events or [])
        if s.done:
            self.trace.episode_end(s.termination, hidden=s.learner)
        return {"output": output, "observation": self.observe(), "done": s.done, "step": s.step}

    # ----------------------------------------------------------- observation --
    def observe(self) -> dict:
        """Serialize Workspace filtered by level. Never includes LearnerState."""
        s = self.state
        ws, lvl = s.workspace, s.instance.level
        base = {"t": ws.t, "step": s.step, "budget": s.instance.budget.model_dump(), "instruction": s.instance.instruction}
        if lvl == 0:
            return {**base, "workspace": ws.model_dump()}
        # level 1/2: only what has been opened + unread counts
        unread = sum(1 for m in ws.messages if not m.read and m.author != "agent")
        return {**base, "open_windows": sorted(self.opened), "unread_messages": unread,
                "hint": "Use files_ls, messages_read_channel, calendar_list, notes_list, browser_visit to look around."}

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
