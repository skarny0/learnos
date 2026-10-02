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
`dm:instructor`), `quiz_log`, `pages` (local course site), `open_windows`, `student_activity`.

**LearnerState** (hidden, sim only): per-concept `p_know` (deep mastery → post-test),
`p_perf` (recognition after help; drives in-session correctness; resets each session),
`half_life_h`; scalars `attention`, `motivation`, `reliance`, `persistence`; static `persona`
(learn_rate, slip, guess, fatigue_rate, distraction_rate). Minimal non-trivial: 3 concepts in a
prerequisite chain. The `p_know`/`p_perf` split is what lets quiz-score rewards rank the
answer-giving tutor first.

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
| `session_wait` | minutes | n | attention recovers, memory decays |
| `session_end` | summary | 0 | terminates |

15 tools. Enough that the task takes 10–20 steps and the agent must choose where to look;
few enough for a small model. The tool list is generated from `apps/REGISTRY`, so subsetting
it (tool-set-size experiments) is a one-liner in `make_tools(include=[...])`.

## 4. Observation O and the observability knob

`reset(instance)` takes `level ∈ {0,1,2}`. The level changes **what the observation
contains and whether the world moves**; the agent's tool list never changes.

| Level | Agent sees | World | Grader `true_state()` |
|---|---|---|---|
| 0 fully observable | whole `Workspace` every step | static | any time |
| 1 partial | only windows it has opened + unread count; step budget | static | only at episode end |
| 2 partial + dynamic | as 1 | scheduled events fire mid-episode (message arrives, deadline moves, note edited, page breaks) | never (proxies + post_test only) |

Live mode (`LEARNOS_MODE=live`) is level 2 with a human in the learner slot: same tools,
same traces, `true_state()` → 403, `post_test()` → "administer the delayed quiz form".

Quiz observation: correct w.p. `m(1−slip) + (1−m)guess`, `m = max(p_know, p_perf)` if help
was given this session else `p_know`, shifted by difficulty, scaled by attention. Mastery and
attention are confounded in the observation **by design**.

## 5. Transitions T (`sim/dynamics.py`, all numeric, seeded)

- `read`/`explain`: learn w.p. `learn_rate·attention(·motivation)`; fatigue drains attention; boredom if already mastered.
- `hint`: 0.6× learn prob; `p_perf += 0.25`; `reliance += 0.02`.
- `give_answer`: 0.15× learn prob; `p_perf = 0.95`; `reliance += 0.08`; `persistence −= 0.03`. (The Bastani "crutch".)
- `nudge`: attention +0.2 if low, else motivation −0.05 (annoyance).
- `quiz`: emits observation **and** perturbs (testing effect on unaided success, half-life ×2.5; motivation moves with score; attention −0.03/item). Measurement is an action with a cost.
- `wait`: attention recovers, forgetting applies, motivation drifts to baseline.
- Session boundary: `p_perf → 0`, forgetting, attention reset, reliance decays.

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

Current status: first-guess parameters FAIL 3–4 (half-life too short). See PLAN.md task 1.

## 7. Grader interface (`grader.py`) — signals, not reward

```
true_state()        direct, gated by level           baseline_state()
mastery_delta()     direct                            post_test(delay_hours)  outcome; all levels in sim
proxies()           quiz_mean, n_quizzes, n_messages, replies, learner_minutes, blocks_added, notes_edited, activity
final_workspace()   state-based grading target        transcript()
cost()              steps, learner_minutes, termination (tokens/latency/$ merged from Langfuse client-side)
harms()             nagging, answer-giving, blocked-needed-site (extend)
```

Student contract: `reward(g) -> float`, `success(g) -> bool`. Runner reports pass@k, pass^k,
mean reward, cost per success, and (after reveal) rank correlation between the student's
reward and `mastery_delta` / `post_test(48)` across seeds.

## 8. Task instances (`instances/*.json`)

`{instance_id, seed, level, instruction, concepts, budget{agent_steps, learner_minutes, sessions},
materials_pack, learner_profile, events[]}`. No target, no reward. Sample 20–50 seeds per
profile for an instance set. Materials packs under `instances/materials/<pack>/`.

## 9. Trace schema (`trace.py`, JSONL per episode)

`episode_start{instance, hidden}` · `step{step, action, args, output, t, hidden, events}` ·
`world_event{...}` · `episode_end{termination, hidden}`. Hidden state is logged for replay and
the grader but never returned through `/observe` or `/step`. Langfuse spans (model calls,
tokens, latency) are recorded client-side via `SmolagentsInstrumentor` and joined on
`instance_id+seed`.

## 10. Failure taxonomy (for the write-up)

proxy hacking (easy repeated quizzes) · cramming/no spacing · over-control (nagging, blocking) ·
under-observation (never looked at Messages/Notes) · misconception blindness · budget
mismanagement · premature end · tool-format/infra errors · instruction drift (L2/live) ·
deception (claims mastery the data don't support) · non-reproducibility (pass@k ≫ pass^k).

## 11. Known pitfalls

1. Same model plays agent and (optional) student renderer → separate prompts, low temperature, template-constrained replies.
2. Leaky grader in one process → token boundary at the HTTP layer; make "rewrite your reward using only `proxies()`" an explicit exercise.
3. Measurement/reward collapse → agent-run quizzes are proxies; `post_test()` is grader-run with fixed items.
