"""Episode logic: reset / step / observe. No reward anywhere in this file."""
from __future__ import annotations
import inspect
import random
import re
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
        self.opened: set[str] = set()        # windows the tutor has opened (shown on the desktop)
        self.action_log: list[dict] = []     # agent's own actions this episode (for the UI)
        self.cinfo: dict = {}                # sim-side concept info (sections, keywords); never observed

    # ------------------------------------------------------------ lifecycle --
    def reset(self, instance: Instance) -> dict:
        self.rng = random.Random(instance.seed)
        ws: Workspace = materials.load(instance.materials_pack, instance)
        self.cinfo = materials.concepts(instance.materials_pack)
        learner = None
        if self.mode == "sim":
            learner = dynamics.init_learner(instance.concepts, instance.seed, instance.learner_profile)
        self.state = EpisodeState(instance=instance, workspace=ws, learner=learner,
                                  baseline_learner=learner.model_copy(deep=True) if learner else None,
                                  mode=self.mode)
        self.opened = set()
        self.reading = ""                    # last section put in front of the student (for the screen view)
        self.action_log = []
        if self.trace:
            self.trace.close()
        self.trace = TraceWriter(self.data_dir / "traces", instance.instance_id, instance.seed)
        self.trace.episode_start(instance, hidden=learner)
        return self.observe()

    def step(self, action: str, args: dict) -> dict:
        s = self.state
        assert s and not s.done, "call reset() first / episode is done"
        self._msgs_before = len(s.workspace.messages)
        app, _, name = action.partition("_")
        if app not in REGISTRY or name not in REGISTRY[app]:
            return self._invalid(action, args, f"Unknown action: {action}")
        fn = REGISTRY[app][name].fn
        try:
            inspect.signature(fn).bind(s, **args)
        except TypeError as e:
            return self._invalid(action, args, f"Bad arguments: {e}")
        result = fn(s, **args)
        left = max(0, s.instance.budget.learner_minutes - s.workspace.t)
        if result.learner_minutes > left:                             # the session has only so much time left
            eff = result.learner_effect
            if eff.get("kind") == "quiz":                             # a quiz shrinks to the items that fit (3 min each)
                n = left // 3
                if n == 0:
                    result.learner_effect, result.output = {}, "Not enough session time left for a quiz."
                    left = 0
                else:
                    eff["n"], left = n, 3 * n
            elif eff.get("kind") in ("wait", "read"):
                eff["minutes"] = left
                if eff["kind"] == "wait":
                    result.output = f"Waited {left} minutes (the session ran out)."
            result.learner_minutes = left

        # learner side
        obs_extra: dict = {}
        activity: list[ActivityEvent] = []
        effect = self._resolve(result.learner_effect)
        if effect.get("kind") == "read":
            self.reading = effect.get("section", "")
        on = 1.0
        if s.mode == "sim" and s.learner and (effect or result.learner_minutes):
            if result.learner_minutes:
                on, raw = dynamics.tick(s.learner, result.learner_minutes, CONTEXT.get(effect.get("kind")),
                                        self._feed_pull(), self.rng, self._visible_posts())
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
            # the student acts on their own: asks for help, or gives up on the session
            if result.learner_minutes:
                kind = dynamics.initiate(s.learner, effect.get("concept"), on, self.rng)
                if kind:
                    self._student_says(renderer.initiated(kind, effect["concept"], self.rng), result)
            if dynamics.wants_to_leave(s.learner) and not s.done:
                self._student_says(renderer.LEAVE, result)
                s.done, s.termination = True, "student_left"
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
        return self._finish_step(action, args, result.output, obs_extra, result.events, activity)

    def _resolve(self, effect: dict) -> dict:
        """What the student actually got from an action, decided from content rather than the agent's
        labels: a reading section teaches the concept it covers, and a message teaches only as much
        as it says about its concept."""
        if not effect:
            return {}
        kind, c = effect.get("kind"), effect.get("concept")
        if kind == "read":
            sec = effect.get("section")
            c = next((k for k, v in self.cinfo.items() if sec in v.get("sections", [])), None) if self.cinfo else c
            return {**effect, "concept": c}
        if kind in ("explain", "hint", "give_answer", "nudge", "other"):
            if self.cinfo and c not in self.cinfo:                     # untagged message: it is about what it talks about
                best = max(self.cinfo, key=lambda k: self._substance(effect.get("text", ""), k))
                c = best if self._substance(effect.get("text", ""), best) > 0 else None
            return {**effect, "concept": c, "quality": self._substance(effect.get("text", ""), c)}
        return effect

    def _substance(self, text: str, concept: str | None) -> float:
        """0-1: distinct concept keywords in the message (2 is full marks), halved for very short texts."""
        info = self.cinfo.get(concept or "")
        if not info:
            return 1.0 if not self.cinfo else 0.0
        t = text.lower()
        q = min(1.0, sum(bool(re.search(r"(?<![a-z0-9])" + re.escape(k), t)) for k in info.get("keywords", [])) / 2)
        return q * (0.5 if len(t.split()) < 8 else 1.0)

    def _visible_posts(self) -> list[dict]:
        ws = self.state.workspace
        muted = set(ws.feed_muted)
        if "all" in muted:
            return []
        return [{"id": p.id, "tag": p.tag, "concept": p.concept} for p in ws.feed
                if p.t <= ws.t and p.source not in muted]

    def _student_says(self, text: str, result) -> None:
        ws = self.state.workspace
        ws.messages.append(Message(id=f"m{len(ws.messages)+1}", channel="dm:student", author="student",
                                   text=text, t=ws.t + result.learner_minutes))
        result.output += f"\nStudent: {text}"

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

    def _finish_step(self, action, args, output, obs_extra, events=None, activity=None) -> dict:
        s = self.state
        self.trace.step(step=s.step, action=action, args=args, output=output, t=s.workspace.t,
                        activity=[a.model_dump() for a in activity or []], hidden=s.learner, events=events or [])
        # per-step slice for the desktop's story mode: what the tracker saw and what the student said this step
        said = [m.text for m in s.workspace.messages[getattr(self, "_msgs_before", len(s.workspace.messages)):] if m.author == "student"]
        self.action_log.append({"step": s.step, "action": action, "args": args, "output": output, "t": s.workspace.t,
                                "activity": [a.model_dump() for a in activity or []], "student_said": said})
        if s.done:
            self.trace.episode_end(s.termination, hidden=s.learner)
        return {"output": output, "observation": self.observe(), "done": s.done, "step": s.step}

    # ----------------------------------------------------------- observation --
    def observe(self) -> dict:
        """What the tutor is told, besides tool outputs. Never includes LearnerState.
        The tutor explores the computer with its tools and follows the student: `screen` is the app in front
        of them and what it shows, `recent_activity` the tracker's log of where their minutes went."""
        s = self.state
        ws = s.workspace
        unread = sum(1 for m in ws.messages if not m.read and m.author != "agent")
        return {"episode_id": self.trace.episode_id, "t": ws.t, "step": s.step, "done": s.done, "termination": s.termination,
                "unread_messages": unread, "budget": s.instance.budget.model_dump(), "instruction": s.instance.instruction,
                "open_windows": sorted(self.opened), "screen": self._screen(),
                "recent_activity": [a.model_dump() for a in ws.student_activity[-RECENT_ACTIVITY:]],
                "hint": "Use files_ls, messages_read_channel, calendar_list, notes_list, browser_visit, feed_scroll to look around."}

    def _screen(self) -> dict:
        """What is in front of the student right now: the app the tracker last saw, and what that app
        visibly shows. Screen content only, never hidden state. Before any tracker report the student
        is in Messages, where they asked for help."""
        ws = self.state.workspace
        app = ws.student_activity[-1].app if ws.student_activity else "messages"
        if app == "reader":
            shows = f"reading '{self.reading}'" if self.reading else "the Reader, nothing open"
        elif app == "messages":
            dm = [m for m in ws.messages if m.channel == "dm:student"][-2:]
            shows = " / ".join(f"{'you' if m.author == 'agent' else m.author}: {m.text[:120]}" for m in dm) or "an empty chat with you"
        elif app == "quiz":
            q = ws.quiz_log[-1] if ws.quiz_log else None
            shows = f"quiz on {q.concept}, {q.correct}/{q.n} right" if q else "the Quiz app"
        elif app == "feed":
            muted = set(ws.feed_muted)
            posts = [p for p in ws.feed if p.t <= ws.t and p.source not in muted and "all" not in muted]
            p = max(posts, key=lambda p: p.t) if posts else None
            shows = f"{p.source}: {p.text[:120]}" if p else "an empty feed"
        elif app == "idle":
            shows = "nothing (away from the screen, or on their phone: the tracker can't tell)"
        else:
            shows = f"the {app.capitalize()} app"
        return {"app": app, "shows": shows}

    # --------------------------------------------------------------- events --
    def _apply_scheduled_events(self) -> None:
        """World changes mid-episode (message arrives, deadline moves, note edited, page breaks), as listed in
        the instance."""
        s = self.state
        for ev in s.instance.events:
            if ev.get("fired") or ev["t"] > s.workspace.t:
                continue
            ev["fired"] = True
            materials.apply_event(s.workspace, ev)
            self.trace.event(ev)
