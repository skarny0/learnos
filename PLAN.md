# Build plan

Phases are ordered by what unblocks the workshop. Each phase ends in something a student
could run. The Python env is the part that must exist regardless; the OS skin is polish.

## Phase 0 — scaffold (done)
State models, 8 app modules (15 tools), seeded sim learner, grader with level gating, JSONL
traces, FastAPI server with websocket feed, placeholder UI, client package with smolagents
tool factory and pass@k/pass^k runner, 2 instances + a materials pack, smoke tests (5 pass).

## Phase 1 — make the sim honest (1–2 days)
1. Tune `sim/dynamics.py` so `python -m learnos_env.sim.validate` passes all four checks.
   Start with `half_life_h` (24h collapses retention to ~1% over 7 days; want 0.45–0.65 →
   ~150–250h for a mastered concept) and the `give_answer` reliance penalty. Keep the
   give_answer/hint ratios inside the Bastani bands.
2. Implement Reader section slicing (`reader.py` TODOs) and quiz items drawn from
   `quiz_bank.json` by concept + difficulty.
3. "Third nudge in 10 steps" penalty; spacing bonus when a scheduled block executes at a
   session boundary.
4. `scripts/cache_trajectories.py`: run 6 fixed policies on 3 seeds, save traces. These are
   the workshop spine.
5. Optional: `renderer.py` LLM paraphrase behind a flag, bins-only prompt, temperature 0.

## Phase 2 — containers that just work (1 day)
1. `docker compose up` on Mac (arm64), Windows (WSL), Linux. Healthcheck, volume perms.
2. `GET /tools` → `make_tools()` → a smolagents `ToolCallingAgent` with `OpenAIServerModel`
   completes `friday-build-01` in ≤ 25 steps. Record a reference trace.
3. Langfuse: `SmolagentsInstrumentor` client-side; join spans to env traces on
   `instance_id+seed`; `client/eval.py` merges tokens/latency into `cost()`.
4. `scripts/make_instances.py`: N seeds × profiles (low prior / high distraction / high
   reliance) from a template.

## Phase 3 — notebooks + cached-trajectory exercise (1–2 days)
`notebooks/01–05` per `notebooks/README.md`. Reward spec sheet as a markdown template in
`02`. Disagreement leaderboard in `04` (rank every pair's reward over the cached traces,
compute rank variance, reveal `true_state`). Rank correlation of each proxy vs
`mastery_delta` across seeds.

## Phase 4 — live mode (1–2 days)
1. `LEARNOS_MODE=live`: `send_to_student` → UI notification (and optional Discord webhook,
   reusing the course's existing Discord setup); `quiz_run` → quiz form in the UI; answers
   `POST /live/quiz_answer`; activity pings `POST /live/activity`; agent runs on a schedule
   (`scripts/live_loop.py`, cron-like, honours quiet hours, ON/OFF blocks for ABAB).
2. Parallel quiz forms A/B/C in `instances/materials/<pack>/quiz_forms.json`.
3. Consent text + kill switch (`touch data/STOP`).
4. `notebooks/06_live.ipynb` with the pre-registration cell (writes reward + timestamp to the volume).

## Phase 5 — the OS skin (2–4 days, parallelisable with 1–4)
Replace `ui/index.html` with a Vite + React desktop in the spirit of ryOS (System-7-ish
windows, dock with exactly the 7 learning apps). It stays a **dumb renderer** of the
websocket payload plus the live-mode input forms. Options: fork ryokun6/ryos (AGPL-3.0) and
strip to 7 apps, or build ~1000 lines fresh. Decide after Phase 2 based on time. Either way
the Zustand store mirrors `Workspace` 1:1 and never holds logic.

## Phase 6 — workshop dry run
Run `docs/workshop-flow.md` end to end with 2–3 volunteers. Time the 7B/API runs. Fix the
three things that break.

## Open decisions (owner: Sheer / Valdemar)
- Model for students: API (`OpenAIServerModel`, as HW5 Part 4) by default; Ollama optional.
- Fork ryOS vs build the skin fresh (decide after Phase 2).
- Discord as the live-mode message channel (reuses Part 6 infra) vs UI-only notifications.
- Whether the hidden-learner layer is required or optional for the base assignment.
