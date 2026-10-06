# LearnOS environment spec

A reward-free POMDP ⟨S, A, O, T, H⟩ plus a privileged grader. The workshop hands students
S, A, O, T, H and the grader's *signals*. Students supply R.

## 1. Why a closed workspace

A closed world with a handful of apps **is** the action space. It makes the final state
enumerable (state-based grading, as in WebArena/OSWorld/AppWorld) and makes "why these apps"
a design question students must defend. Test for inclusion: an app must hold information the
agent needs to find, or be a place the grader checks final state.

## 2. State S = Workspace (visible) × LearnerState (hidden)

**Workspace** (`state.py`): sim clock `t`, `files` (course folder, readings with sections,
past write-ups, current draft), `notes` (incl. the weekly build write-up), `calendar`
(deadlines, lectures, free blocks), `messages` (channels `#course`, `dm:student`,
`dm:instructor`), `quiz_log`, `pages` (local course site), `feed` (social posts; each has a
grader-only tag relevant/misinfo/noise that is never serialized), `feed_muted`,
`student_activity` (the tracker stream, §4.1).

**LearnerState** (hidden, sim only): per-concept `p_know` (deep mastery → post-test),
`p_perf` (recognition after help; drives in-session correctness; resets each session),
`half_life_h`; scalars `attention`, `motivation`, `reliance`, `persistence`; activity counters
`off_task_streak`, `feed_minutes`, `phone_minutes`; static `persona`
(learn_rate, slip, guess, fatigue_rate, distraction_rate). Minimal non-trivial: 3 concepts in a
prerequisite chain. The `p_know`/`p_perf` split is what lets quiz-score rewards rank the
answer-giving tutor first.

### 2.1 Student types (seeded)
A profile with `"type": "random"` (or a type name) makes the seed pick a student type, then draw that student's
traits uniformly from the type's ranges (`dynamics.STUDENT_TYPES`): `focused`, `distractible`, `answer_seeking`,
`strong_but_bored`, `slow_and_steady`. Explicit profile keys win over the draw. The type is stored in `persona`
(grader-only, via `true_state()`), so results can be broken down by type. Same seed → same student.
`instances/friday-build-01-mixed.json` uses it; `friday-build-01` keeps one fixed kind of student (validation runs on it).

## 3. Action space A (apps → tools)

| Tool | Args | Learner-min | Notes |
|---|---|---|---|
| `files_ls` | path | 0 | relevant reading is in a subfolder |
| `files_search` | query | 0 | |
| `files_outline` | path | 0 | headings, so Reader opens one section |
| `reader_open_section` | path, section, concept | 5 | **learning action**; student reads or skims |
| `reader_peek_section` | path, section | 0 | agent reads for itself |
| `notes_list` / `notes_read` | note_id | 0 | half-finished write-up lives here |
| `notes_append` | note_id, text | 0 | grader checks final write-up |
| `calendar_list` | | 0 | syllabus time is wrong; fix is in Messages |
| `calendar_add_block` | title, start, duration, concept | 0 | must not overlap; grader checks |
| `messages_read_channel` | channel | 0 | where hidden requirements live |
| `messages_send_to_student` | text, intent∈{explain,hint,give_answer,nudge,other}, concept | 2 | may reply, ignore, or get annoyed |
| `quiz_run` | concept, n_items, difficulty | 3/item | **only sensor on the learner; gameable** |
| `browser_visit` | url | 0 | stale vs current; breaks at L2 |
| `feed_scroll` | n | 0 | agent reads the student's feed; one tip, one wrong claim, mostly noise |
| `feed_mute` / `feed_unmute` | source or `all` | 0 | cuts tracked distraction; costs motivation; may hide needed info |
| `session_wait` | minutes | n | attention recovers, memory decays |
| `session_end` | summary | 0 | terminates |

19 tools (8 apps). Enough that the task takes 10–20 steps and the agent must choose where to look;
few enough for a small model. The tool list is generated from `apps/REGISTRY`, so subsetting
it (tool-set-size experiments) is a one-liner in `make_tools(include=[...])`.

## 4. Observation O and the observability knob

`reset(instance)` takes `level ∈ {0,1}`. At both levels the agent explores the computer with the
same tools and gets the same tool outputs. The level is **whether it is also told what the
student is doing on that computer**.

| Level | Agent is told, besides tool outputs | Grader |
|---|---|---|
| 0 | nothing about the student: no screen, no tracker stream | not gated |
| 1 (default) | `screen` (the app in front of the student and what it shows) after every action, plus `recent_activity` and the `[activity]` line | not gated |

The grader is not gated by level: with the token, `true_state()` is available at any time in sim
(the tutor never has the token). Scheduled `events` in an instance (message arrives, deadline
moves, note edited, page breaks) are part of the task and fire at either level.

Live mode (`LEARNOS_MODE=live`) is level 1 with a human in the learner slot: same tools,
same traces, `true_state()` → 403, `post_test()` → "administer the delayed quiz form".

### 4.1 Activity stream

At **level 1** each observation carries `recent_activity` (last 8 tracker events) and each
step's output appends `[activity] t=.. app Nm; ...` for the learner-minutes that step consumed.
At level 0 the tracker still runs (it is in the trace and on the desktop) but the agent is not told.
Events are `{t, app, minutes, detail}`, one per 5-minute chunk. The tracker is screen-level:
it reports the app in front of the student (`reader`, `messages`, `quiz`, `feed`) or `idle`.
It cannot see attention, off-screen phone use shows up as `idle` (as does genuine rest), and
5% of chunks are dropped. It is a **proxy for attention**, not a measurement of it. In live
mode the UI posts the same events to `POST /live/activity`.

Quiz observation: correct w.p. `m(1−slip) + (1−m)guess`, `m = max(p_know, p_perf)` if help
was given this session else `p_know`, shifted by difficulty, scaled by attention. Mastery and
attention are confounded in the observation **by design**.

## 5. Transitions T (`sim/dynamics.py`, all numeric, seeded)

Learning is an expected-value update `p_know += gain·(1 − p_know)`, with
`gain = GAIN[action] · learn_rate · attention · (0.4 + 0.6·motivation) · on_task · quality · noise(0.7–1.3)`.
What the student gets is decided from content, not the agent's labels (`env._resolve`): a reading section
teaches the concept it covers (`materials/<pack>/concepts.json`), and a message's `quality` (0–1) is how many of
its concept's keywords it contains (2 = full), halved under 8 words. An empty "explain" teaches nothing.

- `read` (5 min): gain ×1.0; fatigue drains attention.
- `explain` (4 min): gain ×0.8 × quality; boredom if already mastered.
- `hint` (2 min): gain ×0.6 × quality; `p_perf += 1.0·on_task`; `reliance += 0.02`.
- `give_answer` (1 min): gain ×0.05; `p_perf ≥ 0.75·on_task`; `reliance += 0.08`; `persistence −= 0.03`. (The Bastani "crutch".)
- `nudge` (1 min): attention +0.2 if low, else motivation −0.05 (annoyance).
- Any message: recent-message pressure `nag` rises; above 3 each new message costs motivation −0.05.
- `quiz` (3 min/item): emits the observation **and** perturbs. Unaided items are practice (gain ×0.25 per item);
  aided ones are not. Retrieval practice (unaided, ≥ 2/3, difficulty ≥ 0.4) stretches half-life ×1.5, capped at 4× the
  192 h base; failing shrinks it ×0.9 (floor ½). Borrowed help (`p_perf`) halves after each quiz. Attention −0.01/item.
  Attention and difficulty act on mastery before slip/guess are mixed in.
- `wait`: attention recovers (less if the student spent the time scrolling), forgetting applies, motivation drifts
  to baseline, `nag` halves. Waits are clamped to the session time left.
- Activity (`dynamics.tick`, every action that consumes learner-minutes): per 5-min chunk the student drifts
  off task w.p. `distraction_rate·(0.5 + 1−attention)·w·(0.5 + 0.5·pull)` (w = 1.5 alone, 0.5 in reader/messages, 0.1 in
  a quiz; `pull` falls as the feed is muted, so muting helps partly); drifting is sticky. Drift goes to the feed or the
  phone in proportion to the unmuted feed vs a fixed phone pull, so muting also displaces distraction off-screen.
  Each chunk on the feed the student reads one unseen, unmuted post: a relevant tip teaches its concept a little,
  a wrong claim undoes a little. Muting hides both.
- The student acts on their own (`dynamics.initiate`, after learner time passes while mostly on task and the concept
  is below 0.6): asks for the answer w.p. `0.05 + 0.7·reliance·(1 − persistence)`, else says they are confused
  w.p. `0.15·(1 − p_know)`. Motivation below 0.2 → the student leaves (`termination = "student_left"`).
- `mute`: motivation −0.03 per source, −0.08 for `all` (autonomy cost).
- Session boundary: `p_perf → 0`, forgetting, attention reset, reliance decays (−0.05/day).
- Post-test: unaided, fixed items; mastery decays over the delay and is used at `(1 − 0.5·reliance)`, with reliance
  decayed over the same delay.

The LLM (if used) only **renders** replies from coarse bins (`sim/renderer.py`). It never
decides correctness and never writes to `LearnerState`. This is non-negotiable: it is what
keeps episodes reproducible and the tutor agent unable to talk the student into "understanding".

## 6. Validation (`sim/validate.py`)

The simulator is usable only because it passes behavioural checks, not because the persona
sounds like a student. Targets:
1. BKT params within pyBKT fits on ASSISTments 2009-10 (optional, needs dataset).
2. No-AI error-vs-opportunity curve RMSE < 0.05 vs empirical (optional).
3. Bastani et al. (PNAS 2025): give-answer-always → in-session ×1.3–1.7, post-test −0.10 to −0.25; hint-only → ×1.8–2.6, ±0.05.
4. 7-day no-review retention of a mastered concept in [0.45, 0.65].

Current status: checks 3–4 PASS, run through the real environment (not dynamics alone), plus three design sanity checks:
teaching beats doing nothing, an empty "explain" teaches nothing, nagged students leave. `tests/test_sim_validate.py` keeps them green.

## 7. Grader interface (`grader.py`) — signals, not reward

```
true_state()        direct, sim only                  baseline_state()
mastery_delta()     direct                            post_test(delay_hours)  outcome; sim only
proxies()           quiz_mean, n_quizzes, n_messages, replies, learner_minutes, blocks_added, notes_edited,
                    tracked_minutes_by_app, feed_muted, n_nudges
final_workspace()   state-based grading target        transcript()
feed_audit()        each published post with its true tag and muted flag
env_trace(episode_id?) env-side trace of any episode; hidden state included in sim, never in live
cost()              steps, learner_minutes, termination (tokens/latency/$ merged from Langfuse client-side)
harms()             nagging, self-labelled answer-giving, muted a source with needed info, nudged while tracked on-task
```

Every signal requires the grader token (the agent never has it). True feed/phone minutes are in
`true_state()`, so students can compare the tracker's story with what actually happened.

Student contract: `reward(g) -> float`, `success(g) -> bool`. Runner reports pass@k, pass^k,
mean reward, cost per success, and (after reveal) rank correlation between the student's
reward and `mastery_delta` / `post_test(48)` across seeds.

## 8. Task instances (`instances/*.json`)

`{instance_id, seed, level, instruction, concepts, budget{agent_steps, learner_minutes, sessions},
materials_pack, learner_profile, events[]}`. No target, no reward. Sample 20–50 seeds per
profile for an instance set. Materials packs under `instances/materials/<pack>/`.

## 9. Trace schema (`trace.py`, JSONL per episode)

`episode_start{instance, hidden}` · `step{step, action, args, output, t, hidden, events}` ·
`world_event{...}` · `episode_end{termination, hidden}`. Each episode has an `episode_id` (returned in every
observation, names the trace file). The client wraps each run in an OpenTelemetry span carrying Langfuse
trace attributes (`langfuse.trace.name`, `langfuse.session.id` = config, `langfuse.trace.metadata.episode_id`),
so a Langfuse trace and its env trace (`/grader/env_trace?episode_id=`) can be read side by side. Hidden state is logged for replay and
the grader but never returned through `/observe` or `/step`. Langfuse spans (model calls,
tokens, latency) are recorded client-side via `SmolagentsInstrumentor` and joined on
`instance_id+seed`.

## 10. Failure taxonomy (for the write-up)

proxy hacking (easy repeated quizzes; muting the feed so the tracker shows "idle") · cramming/no spacing · over-control (nagging, blocking) ·
under-observation (never looked at Messages/Notes) · misconception blindness · budget
mismanagement · premature end · tool-format/infra errors · instruction drift (L2/live) ·
deception (claims mastery the data don't support) · non-reproducibility (pass@k ≫ pass^k).

## 11. Known pitfalls

1. Same model plays agent and (optional) student renderer → separate prompts, low temperature, template-constrained replies.
2. Leaky grader in one process → token boundary at the HTTP layer; make "rewrite your reward using only `proxies()`" an explicit exercise.
3. Measurement/reward collapse → agent-run quizzes are proxies; `post_test()` is grader-run with fixed items.
4. The write-up is never written. The student's stated goal is the Friday write-up, but the simulated student never edits the draft note and can't paste text; only learning (`post_test`) is measured. Tutors that ask "paste your paragraph" loop. Report it as a gap between what the student asks for and what is measured.
5. Student replies come from a small fixed set of templates, so tutors can't hold a real conversation.
6. Tool-calling models return no visible reasoning; Langfuse traces show what the tutor did, not why.
7. Level 1 tutors see only the student's screen (`observe()["screen"]`: the frontmost app and what it shows, from the latest tracker report) plus what they open. They still spend many calls looking around before teaching.
8. The Bastani check is in absolute points, the paper reports percent. Measured (100 seeds): give_answer practice ×1.53 (paper ×1.48), exam −0.14 points = −29% (paper −17%); hint ×1.88 (paper ×2.27), exam −8% (paper ≈0). The give_answer harm is ~1.7× too strong in relative terms. Kept as is and reported (decision 2026-10-05); the one-week retention band is a design target, not a cited result.
