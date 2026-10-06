# LearnOS — a reward-free learning workspace for agents

A simulated "student's computer" limited to learning apps (Files, Reader, Notes,
Calendar, Messages, Quiz, Browser) plus a social Feed the student gets distracted by. A tracker
streams what the student is doing (reading, scrolling, idle) into every observation. An agent navigates it through a tool API to
help a (simulated or real) student. The environment ships **without a reward
function**: students define success themselves and grade against the final
workspace state, plus an optional hidden-learner layer.

Built for the *Cognitive Agents* workshop, week on environments & evaluation
(MIT, Valdemar Danry / Sheer).

## Start here

```bash
make build     # once: venv + packages + .env  (needs Python 3.12 or uv; no Docker, no Node)
make start     # runs LearnOS, opens the desktop, plays a demo episode
```

New to the project? Read `docs/onboarding.md` (15 minutes). `make` lists every command
(`make notebook`, `make test`, `make up` for Docker, `make doctor` if something's off).

## In a notebook (Colab or Jupyter), no Docker

The workshop is one notebook: `notebooks/learnos_workshop.ipynb`
([open in Colab](https://colab.research.google.com/github/skarny0/learnos/blob/master/notebooks/learnos_workshop.ipynb)).
Its first cell clones this repo in Colab. Keys: in Colab, add `OPENAI_API_KEY` (and optionally
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`) under the key icon (Secrets), or type them
when the notebook asks. Locally, put them in `.env`. No key: every cell uses recorded runs.


```python
%pip install -q -e learnos/env -e learnos/client     # after cloning the repo
from learnos_client import start, show, make_tools
env = start()      # LearnOS server inside the kernel; returns a client holding the grader token
show()             # the desktop, embedded and live below the cell (show_in_tab() for a full tab)
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
| `sim` (default) | simulated learner in `env/learnos_env/sim` | available | workshop, pass^k runs |
| `live` | the human at localhost:8080 | 403 | 2-day in-the-wild deployment |

## Observability levels (set per episode on `reset`)

At both levels the tutor explores the computer with the same tools. The level is whether it is also told what the student is doing on it.

- **0** the tutor is not told what the student is doing: no screen, no tracker stream. Only what the tools return.
- **1** (default) the tutor follows the student: after every action it is told which app is in front of them and what it shows, plus the tracker stream.

Mid-episode world changes (a message arrives, the deadline moves) are listed per task in `instances/*.json` under `events` and fire at either level.

See `docs/environment-spec.md`. Build plan in `PLAN.md`. Handoff for Claude Code in `CLAUDE.md`.
