# CLAUDE.md — handoff for Claude Code

You are continuing a scaffolded repo. Read `README.md`, `PLAN.md`, `docs/environment-spec.md`
first. Work through `PLAN.md` phases in order; each phase ends in something runnable.

## What this is
A reward-free "student's computer" environment (7 learning apps + a social Feed, 19 tools,
plus a streamed student-activity tracker) that an agent
navigates via an HTTP API, with a seeded simulated learner whose cognitive state is hidden,
and a privileged grader that exposes signals (never a reward). Students write the reward.
Ships as `docker compose up`. Two modes: `sim` (workshop, pass^k runs) and `live` (the
human is the learner for 2 days).

## Non-negotiables (do not "simplify" these away)
1. **No reward anywhere in `env/`.** The grader returns signals; `reward()`/`success()`
   live only in student code and `client/eval.py` takes them as arguments.
2. **Hidden state is numeric and updated only in `sim/dynamics.py`.** An LLM may paraphrase
   student text in `sim/renderer.py`; it never decides correctness or writes to `LearnerState`.
3. **`/observe` and `/step` never serialize `LearnerState`.** Test exists; keep it green.
4. **Observability is a per-episode `level`, not separate environments.** Level only changes
   the observation builder, the grader's gating, and whether L2 events fire. The tool list
   is constant.
5. **Measurement is an action with cost.** `quiz_run` consumes learner-minutes and perturbs
   state. The grader's `post_test()` is the fixed-item, agent-independent outcome.
6. **The UI is a dumb renderer** of the websocket payload (+ live-mode input forms). No
   logic in the UI. Zustand store mirrors `Workspace` 1:1.
7. **Same tool names in sim and live.** Live swaps backends, never the API.

## Conventions
- Python 3.12, FastAPI, Pydantic v2, no ORM (JSON/JSONL on the volume is fine).
- Apps are pure functions `(EpisodeState, **args) -> ActionResult` registered in
  `apps/REGISTRY`. New tool = new function + decorator. The registry generates the smolagents
  tools; never hand-write tool lists elsewhere.
- Every action that touches the learner returns `learner_effect`; `env.step` hands it to
  `dynamics.apply`. Keep that single seam.
- Traces are JSONL per episode in `data/traces/`. Hidden state is logged there (for replay
  and grading) but never returned by the API.
- Tests: `cd env && pytest`. Sim validation: `python -m learnos_env.sim.validate` (currently
  FAILs 4 of 5 on first-guess params; Phase 1 task 1 is to make it pass without breaking the
  Bastani bands).
- Run it: `make build` once, then `make start` (no Docker; desktop + API on `:8000`). `make` lists targets.
  Docker: `make up` / `docker compose up`; API `:8000` (`/docs` for OpenAPI), UI `:8080`.
- Set `LEARNOS_INSTANCES_DIR=../instances` when running env code outside Docker.
- Every grader signal needs the token, including `proxies()` and `post_test()`.
- `dynamics.tick` decides what the student does while learner-minutes pass; the tracker stream
  it emits is screen-level and noisy on purpose. Its parameters are first guesses, not validated.

## First three things to do
1. Phase 1.1: tune `half_life_h` and the `give_answer` reliance penalty until
   `validate.py` prints 5× PASS. Add a pytest that asserts it.
2. Phase 1.4: `scripts/cache_trajectories.py` with six scripted policies; save traces;
   add `scripts/replay_trace.py` that pushes a trace through the websocket so the UI replays it.
3. Phase 2.2: end-to-end `ToolCallingAgent` + `OpenAIServerModel` run on `friday-build-01`
   via `client/learnos_client`. Commit the reference trace to `data/reference/`.

## Things to ask Sheer/Valdemar before deciding
- Fork ryOS vs build the skin fresh (Phase 5).
- Discord vs UI-only for live-mode messages.
- Whether the hidden-learner layer is required for the base assignment or an extension.

## Context docs
`docs/environment-spec.md` (the contract), `docs/workshop-flow.md` (how it's used in class),
`notebooks/README.md` (what students see). Design rationale and the five-lens brainstorm are
in the course project doc `environment-design-fanout.md`.
