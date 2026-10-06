# Onboarding: LearnOS in 15 minutes

## 1. Run it (2 min)
```bash
make build     # once: Python venv with both packages + Jupyter, and a .env
make start     # starts LearnOS, opens the desktop, plays a 16-step demo episode on it
```
Needs Python 3.12 (or `uv`). No Docker, no Node. `make doctor` says what's missing; `make` lists every command.

## 2. What you're looking at (3 min)
A fake **student's laptop**: Files, Reader, Notes, Calendar, Messages, Quiz, Browser, and a social **Feed**
the student drifts to. An **agent** (a tutor) operates the laptop through 19 tools over HTTP. While it works,
a **tracker** streams what the student is doing (reading, scrolling the feed, idle) into every observation.

The student is **simulated**: hidden numbers (how well they know each concept, attention, motivation) that
move according to rules from the learning-science literature. The agent never sees those numbers.

**There is no reward.** A privileged **grader** exposes signals (post-test score, time spent, what the
agent did), and *students write the reward*. That's the point of the course: decide what "good tutoring" means,
measure it, and see where your measure goes wrong.

While the demo plays, watch:
- **Agent Log** (🤖 in the dock): each tool call as it happens.
- **Activity Monitor** (📈): the tracker stream, i.e. what the student was doing between agent actions.
- **Feed**: the agent mutes `#memes` at step 12. **Calendar** gets a study block, and **Notes** gets a scaffold.

Run `make demo` to replay it.

## 3. Drive it yourself (5 min)
`make notebook` opens `notebooks/learnos_workshop.ipynb`, the whole workshop in one notebook: start the server
in the kernel, embed the desktop, drive it by hand, peek at the grader, replay real AI tutor runs, read the
Langfuse trace next to the student's record, then design your own tutor (put `OPENAI_API_KEY` in `.env`;
without it the notebook uses recorded runs).

API docs: http://localhost:8000/docs.

## 4. Where things live (3 min)
| You want to change… | Look in |
|---|---|
| a tool / app (what the agent can do) | `env/learnos_env/apps/*.py`: one function plus a decorator, auto-registered |
| how the student responds | `env/learnos_env/sim/dynamics.py`: the **only** place hidden state changes |
| what the agent observes | `env/learnos_env/env.py` (`observe`, levels 0/1) |
| what the grader exposes | `env/learnos_env/grader.py` (token-gated signals, never a score) |
| a task: materials, deadlines, mid-episode events | `instances/*.json`, `instances/materials/` |
| the desktop | `ui/src/` (React; `make ui` rebuilds into `env/learnos_env/ui_dist`) |
| agent tools + eval runner (pass@k, pass^k, Langfuse links) | `client/learnos_client/` |

## 5. Rules of the repo (2 min)
These are the full list in `CLAUDE.md`; the important ones:
1. **No reward or judgment in `env/`.** No scores, no "this was bad" labels. Students write those.
2. Hidden learner state changes **only** in `sim/dynamics.py`, and the API **never** returns it.
3. Measuring the student (a quiz) is an action, and it costs the student's time.
4. The UI only renders state; it contains no logic.

`make test` must stay green.

## Next: what's built, what isn't
- `docs/curriculum.md`: the module-by-module plan (M0–M6) and what each module needs from the env.
- `PLAN.md`: build phases. The most urgent open item: **tune the simulator** (`make validate` currently fails
  4 of 5 checks), because until then good and bad tutoring produce nearly the same outcomes.
- `docs/environment-spec.md`: the full contract.
