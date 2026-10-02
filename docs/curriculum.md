# Curriculum: one agent, one trace, built forward

Students keep the same agent the whole way. Each module adds one thing to the environment and one skill to
the student's evaluation toolkit, and **starts from what the previous module's traces could not answer**.
The environment never says what is good (see CLAUDE.md non-negotiable 1); each module asks students to
write or revise their own definition.

```
M0 agent ─▶ M1 two traces ─▶ M2 own reward ─▶ M3 hidden + moving world ─▶ M4 many learners
                                                                              │
                         M7 in the wild ◀── M6 classroom ◀── M5 new cognitive brick
```

What students carry forward, growing each module:
**agent** (prompt, tools, guardrails) · **detectors** (their own trace predicates: "did it give answers?") ·
**reward / success** (their own functions over grader signals) · **a trace log** (every run, both traces, linked
by `episode_id`).

---

## M0 — First agent
- **Question:** what does my agent actually do on a student's laptop?
- **Environment:** one student, level 0 (agent sees everything), one topic pack. Desktop UI shows the run live.
- **Students build:** a smolagents agent using `make_tools(env)`; run it a few times and watch the desktop.
- **Observability skill:** read one Langfuse trace end to end.
- **Carries forward:** agent v0 and its first traces.
- **Status:** built.

## M1 — Two traces (workshop Part 5)
- **Seed from M0:** the Langfuse trace shows what the agent did, but not what happened to the student.
- **Environment:** the env trace (`env_trace(episode_id)`), linked to Langfuse; the student activity stream.
- **Students build:** **detectors**, small functions over a trace that flag behaviour they care about.
  Diagnose bad runs as reasoning / tool output / prompt / infrastructure / **observation**.
- **Observability skill:** read the two traces side by side, and find a run where the agent's view was wrong.
- **Carries forward:** detectors and a list of failures they want gone.
- **Status:** built (`notebooks/part5_observability.ipynb`).

## M2 — Write your own reward, then climb it
- **Seed from M1:** the failures they listed. Now they have to turn "good tutoring" into code.
- **Environment:** grader signals, tagged direct vs proxy and never ranked; fixed **dev / held-out seed sets**;
  a **guardrail hook** (`make_tools(guard=fn)`); `log_scores()` that sends *their* functions' outputs to Langfuse.
- **Students build:** `reward()` / `success()`; guardrails motivated by M1 failures; then hill-climb the agent
  on dev seeds (prompt, tools, guardrails), watching their own reward in Langfuse.
- **Observability skill:** dashboards of their own scores; then check held-out seeds and the direct signals.
  Did climbing their reward also move `post_test`? (Goodhart, measured on their own work.)
- **Carries forward:** reward v1, agent v1, guardrails.
- **Status:** needs sim tuning (outcomes are currently flat), seed sets, guard hook, `log_scores`.

## M3 — Partial observability and a moving world
- **Seed from M2:** their reward and agent were built at level 0, where everything is visible.
- **Environment:** level 1 (sees only what it opens), level 2 (world changes mid-run: messages, deadlines,
  feed posts); the noisy activity tracker (a phone looks like "idle").
- **Students build:** agent v2 that gathers information on purpose; reward v2 that only uses signals available
  at that level.
- **Observability skill:** list what neither the agent nor the reward can see, and where traces disagree with
  hidden state.
- **Carries forward:** a reward that survives partial observability.
- **Status:** built (levels, feed, tracker); depends on M2's tuning for meaningful outcomes.

## M4 — Many kinds of learners
- **Seed from M3:** every result so far came from a handful of similar students.
- **Environment:** a library of **learner types** (recipes of brick settings: slow, distractible,
  answer-seeking, bored-and-strong, ...) and a sweep runner: many seeds per type.
- **Students build:** run agent v2 across types; break results down by type.
- **Observability skill:** aggregate traces by learner type. Does the average hide a group the agent fails?
  Is pass^k stable within a type?
- **Carries forward:** a per-type report; maybe agent v3 that adapts to the learner.
- **Status:** needs the brick refactor and the learner-type library.

## M5 — Add a cognitive brick
- **Seed from M4:** the student model only covers learning, attention and reliance. What about critical
  thinking, engagement, curiosity, confidence?
- **Environment:** the **construct plugin** interface. Each brick has hidden numbers, rules for change,
  measurement instruments, optional new tools, and validation checks it must pass.
- **Students build:** a new brick (worked example: *critical thinking*, i.e. does the student believe
  unverified feed posts), with an instrument and one known effect it must reproduce.
- **Observability skill:** re-evaluate the old agent and reward against the new outcome. Their reward almost
  certainly ignores it. What else is it ignoring?
- **Carries forward:** a validated brick (shared with the class); reward v3.
- **Status:** needs the brick refactor.

## M6 — The classroom (tabled)
- **Seed from M4–M5:** one tutor per student does not scale; real teachers share their time.
- **Environment:** one teacher agent, N students of mixed types in one episode; per-student activity streams
  and DMs; the budget is the teacher's time. One-on-one becomes a class of size 1, so all earlier tools still work.
- **Students build:** a teacher agent that allocates attention across students; a class-level reward
  (mean? worst student? equity across types?).
- **Observability skill:** traces become per-student timelines inside one run; find who got neglected and why.
- **Carries forward:** teacher agent; a stance on what "good for a class" means.
- **Status:** tabled for now (2026-10-01). Open question if revived: do students affect each other?

## M7 — In the wild
- **Seed from everything:** all of this was simulated.
- **Environment:** live mode, where the human is the student; same tools, same traces, no hidden state.
- **Students build:** pre-registered reward, ABAB protocol (see `workshop-flow.md`).
- **Observability skill:** compare their sim traces with traces of themselves. What did the simulator get wrong?
- **Status:** planned (PLAN.md Phase 4).

---

## The worksheet
The Colab notebook (`Cognitive_Agents_Environments_Tutorial.ipynb`) is the worksheet the whole curriculum builds
on. One notebook, one section per module, in the same style as the current tutorial (Problems with point values,
`CHANGE ME` blocks, deliverables). Students define their agent, detectors and reward once, near the top, and later
sections extend or redefine them instead of starting over. Their Langfuse project accumulates every run across
modules, so later sections can query back to earlier traces.

| Worksheet section | Module |
|---|---|
| Setup: `start()` runs LearnOS in the kernel, `show()` embeds the desktop, Langfuse keys | — |
| Part 1–2: reading, eval design (existing) | framing |
| Part 3: build the agent | M0 |
| Part 5: observability (`notebooks/part5_observability.ipynb`) | M1 |
| Reward spec + hill-climbing | M2 |
| Later sections | M3–M7 |

Because it runs in Colab, LearnOS must start **inside the Colab VM** (Colab cannot reach a student's Docker).

## How this maps to the current course
The 120-minute workshop in `workshop-flow.md` is **M1 + M2** compressed (with cached trajectories standing in
for M0), and its 2-day take-home is **M7**. M3–M6 are extensions or later weeks.

## What the environment needs, in curriculum order
| For | Build | Status |
|---|---|---|
| M2 | sim tuning so outcomes have a slope (Phase 1.1) | next |
| M2 | neutral `harms()` (counts, not verdicts) | next |
| M2 | dev / held-out seed sets, `log_scores()`, guardrail hook | todo |
| M4, M5 | construct ("brick") refactor of the learner model | todo |
| M4 | learner-type library + sweep runner | todo |
| M5 | critical-thinking brick as the worked example | todo |
| M6 | multi-student episodes (`student` arg, defaulting to the only one) | tabled |
| M7 | live-mode UI forms, activity reporting | partial |
