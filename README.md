# LearnOS — a reward-free learning workspace for agents

A simulated "student's computer" limited to learning apps (Files, Reader, Notes,
Calendar, Messages, Quiz, Browser) plus a social Feed the student gets distracted by. A tracker
streams what the student is doing (reading, scrolling, idle) into every observation. An agent navigates it through a tool API to
help a (simulated or real) student. The environment ships **without a reward
function**: students define success themselves and grade against the final
workspace state, plus an optional hidden-learner layer.

Built for the *Cognitive Agents* workshop, week on environments & evaluation
(MIT, Valdemar Danry / Sheer).

## Quick start (students)

```bash
docker compose up            # env API on :8000, workspace UI on :8080
pip install -e client/       # smolagents tools that talk to the env
jupyter lab notebooks/       # 01_tour.ipynb
```

## Layout

```
env/        FastAPI service. Owns canonical state, seeded reset/step, grader, traces.
ui/         Web desktop (Vite + React + Zustand) that renders env state over a websocket. No logic.
            Dev: `cd ui && npm install && npm run dev` (:5173, proxies to the env on :8000).
client/     Python package: smolagents Tool classes + thin HTTP client + eval runner.
instances/  Task instances (seed + materials + budget). No targets, no rewards.
docs/       Environment spec, observability levels, grader interface, workshop flow.
notebooks/  Student-facing notebooks.
data/       Docker volume: state.db, traces/ (persists the 2-day in-the-wild run).
scripts/    Dev helpers (make_instances, replay_trace, validate_sim).
```

## Two modes, one container

| `LEARNOS_MODE` | Who is the student | Grader `true_state()` | Use |
|---|---|---|---|
| `sim` (default) | simulated learner in `env/learnos_env/sim` | available (level 0/1) | workshop, pass^k runs |
| `live` | the human at localhost:8080 | 403 | 2-day in-the-wild deployment |

## Observability levels (set per episode on `reset`)

- **0** full workspace state returned every step
- **1** agent only sees what it opens; step budget applies
- **2** level 1 + the world changes during the episode (new messages, moved deadlines, edits)

See `docs/environment-spec.md`. Build plan in `PLAN.md`. Handoff for Claude Code in `CLAUDE.md`.
