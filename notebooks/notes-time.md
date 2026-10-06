# How time works in LearnOS (companion note, not workshop material)

Time is a simulated clock in **student-minutes**. It only moves when the tutor spends the student's time.
Nothing happens between tutor calls, and wall-clock time is never involved.

## 1. The clock
| Tool call | Student-minutes |
|---|---|
| `reader_open_section` | 5 |
| `messages_send_to_student` | explain 4 · hint 2 · give_answer 1 · nudge 1 · other 1 |
| `quiz_run` | 3 per question |
| `session_wait` | 5–60, the tutor's choice |
| everything else (files, notes, calendar, browser, feed, peeking at a reading) | 0 |

A session has a budget of 90 student-minutes (and 40 tool calls). A quiz that doesn't fit is shrunk; a wait or
reading that doesn't fit is clamped; when the budget is used the episode ends (`termination: learner_minutes`).
Calendar times are minutes from session start (the Friday build is at t=2640, about 44 h).

## 2. What the student does while minutes pass (`dynamics.tick`)
The minutes run in 5-minute chunks. Each chunk the student is on task or drifts: the chance rises with their
distraction trait and tiredness, is highest when left alone (`session_wait`), lowest during a quiz, and once they
are off task it tends to stay that way. Drift goes to the feed (tracked) or the phone (reported as `idle`).
On the feed they read one unseen post: a relevant tip teaches a little, a wrong claim undoes some knowledge.
These chunks are the tracker events. So a 30-minute wait is six rolls of the drift dice, not empty time.

## 3. Recovery and wear
- Attention: −fatigue per reading minute and per quiz question; recovers during waits (less if they scrolled).
- Message pressure (`nag`): ×0.7 then +1 per message; ×0.5 per wait. Above 3, each message costs motivation.
- Motivation drifts back toward 0.6 during waits.

## 4. Forgetting
Each idea has a memory half-life, 192 h (8 days) at the start, stretched ×1.5 by a passed unaided quiz at real
difficulty (cap ×4), shrunk ×0.9 by a failed one. Decay applies in two places only:
- during `session_wait`, over the minutes waited;
- across the delay before the post-test (`post_test(delay_hours=48)`), where reliance also fades by 0.05 per day
  and borrowed help (`p_perf`) does not count.

## Known quirk
Within the session, forgetting ticks only during `session_wait`. The minutes spent on a reading, a message or a
quiz do not decay the other ideas. At an 8-day half-life the difference is negligible (5 minutes ≈ 0.03% of
knowledge), but it is an inconsistency in the rules, not a design choice. Fixing it means applying the same
decay in `dynamics.apply` for every action's `learner_minutes`; the validation checks would need rerunning.

Code: `env/learnos_env/sim/dynamics.py` (`apply`, `tick`, `post_test`, `session_boundary`), `env/learnos_env/env.py` (budget clamp).
