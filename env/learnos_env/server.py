"""FastAPI surface.

Agent-facing:   POST /reset  POST /step  GET /observe  GET /tools  GET /health
Grader-facing:  GET /grader/{signal}   (header X-Grader-Token; 403 in live mode for direct signals)
UI-facing:      WS  /ws  (full Workspace pushed after every step; UI is a dumb renderer)
Live mode:      POST /live/quiz_answer  POST /live/activity  POST /live/student_message
"""
from __future__ import annotations
import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .env import LearnOSEnv
from .grader import GraderView, Unavailable
from .state import Instance, QuizResult, ActivityEvent
from .apps import tool_specs

MODE = os.environ.get("LEARNOS_MODE", "sim")
TOKEN = os.environ.get("LEARNOS_GRADER_TOKEN", "change-me")
DATA = Path(os.environ.get("LEARNOS_DATA_DIR", "./data"))

app = FastAPI(title="LearnOS env", version="0.0.1")
env = LearnOSEnv(DATA, MODE)
_subscribers: set[WebSocket] = set()


class StepReq(BaseModel):
    action: str
    args: dict = {}


async def _broadcast():
    if not env.state:
        return
    st = env.state
    payload = {"workspace": st.workspace.model_dump(), "step": st.step, "done": st.done,
               "termination": st.termination, "mode": MODE, "instance_id": st.instance.instance_id,
               "level": st.instance.level, "budget": st.instance.budget.model_dump(),
               "agent_opened": sorted(env.opened), "action_log": env.action_log[-50:]}
    dead = []
    for ws in _subscribers:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _subscribers.discard(ws)


@app.get("/health")
def health():
    return {"ok": True, "mode": MODE}


@app.get("/tools")
def tools():
    return tool_specs()


@app.post("/reset")
async def reset(instance: Instance):
    obs = env.reset(instance)
    await _broadcast()
    return obs


@app.post("/step")
async def step(req: StepReq):
    if not env.state:
        raise HTTPException(400, "reset first")
    if env.state.done:
        raise HTTPException(409, f"episode is done ({env.state.termination}); reset first")
    out = env.step(req.action, req.args)
    await _broadcast()
    return out


@app.get("/observe")
def observe():
    if not env.state:
        raise HTTPException(400, "reset first")
    return env.observe()


# ------------------------------------------------------------------ grader --
@app.get("/grader/{signal}")
def grader(signal: str, delay_hours: float = 0.0, x_grader_token: str | None = Header(default=None)):
    if not env.state:
        raise HTTPException(400, "reset first")
    g = GraderView(env.state, token_ok=(x_grader_token == TOKEN))
    try:
        if signal == "post_test":
            return {"post_test": g.post_test(delay_hours)}
        fn = getattr(g, signal, None)
        if not fn or signal.startswith("_"):
            raise HTTPException(404, f"no signal {signal}")
        return fn()
    except Unavailable as e:
        raise HTTPException(403, str(e))


# ---------------------------------------------------------------------- ui --
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    _subscribers.add(websocket)
    await _broadcast()
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _subscribers.discard(websocket)


# -------------------------------------------------------------------- live --
# In live mode the human is the learner. The UI posts what they do; these land in Workspace
# exactly where the sim would have put them, so the agent code does not change.
def _live_state():
    if MODE != "live":
        raise HTTPException(400, "live mode only")
    if not env.state:
        raise HTTPException(400, "reset first")
    return env.state


@app.post("/live/quiz_answer")
async def live_quiz_answer(result: QuizResult):
    _live_state().workspace.quiz_log.append(result)
    await _broadcast()
    return {"ok": True}


@app.post("/live/activity")
async def live_activity(event: ActivityEvent):
    """The live UI's tracker posts what the human is doing; same schema the sim streams."""
    _live_state().workspace.student_activity.append(event)
    await _broadcast()
    return {"ok": True}
