# Workshop flow (120 min) + take-home

Spine = 6–8 **cached trajectories** (give_answer-always, hint-only, honest-slow, teach-to-test,
over-nudger, never-looked-at-messages). Live model runs are a bonus, not the critical path.

| Min | Activity |
|---|---|
| 0–10 | Hook: replay one cached trajectory in the UI. Vote: good tutor or bad? (It scores 100% on quizzes; hidden mastery is flat.) Reveal nothing. |
| 10–25 | Mini-lecture: direct vs proxy; evaluation taxonomy rows; pass@k vs pass^k; cost. "You will have to pick a row." |
| 25–40 | **Reward spec sheet** (pairs, written before the notebook unlocks): signals used; each tagged direct/proxy; executable grading rule; horizon; what it would miss / how an agent games it; taxonomy row. |
| 40–60 | Run `reward()`/`success()` on the cached trajectories + 2–3 live runs with Langfuse. Report pass@3, pass^3, cost. |
| 60–75 | **Disagreement moment**: leaderboard of the same trajectories under every pair's reward; project the highest-variance one; pairs defend; then `true_state()` reveal. |
| 75–85 | Known/unknown worksheet: mastery, attention, motivation, 24h retention, cost, latency, agent self-confidence × (observable in sim? in wild? proxy? confound?). |
| 85–100 | Discussion tied to lecture: evaluating cognitive outcomes without ground truth; which taxonomy row now vs after the wild phase; is an LLM judge a proxy; when pass^k matters for a tutor. |
| 100–110 | Reward spec v2. |
| 110–120 | Take-home setup: `LEARNOS_MODE=live`. |

## Take-home (2 days, in the wild, n-of-1)

1. Pre-register reward v2 as runnable code + primary metric + minimum effect; commit with timestamp.
2. Baseline quiz (form A).
3. ABAB half-day blocks, counterbalanced; OFF = agent logs but actions are no-ops.
4. Same check-in cadence and quiz burden in both conditions.
5. Post quiz (form B) end of day 2; delayed quiz (form C) ~day 4; transfer = build write-up rubric.
6. Report: R per block, ON−OFF with 4-block variance, proxy–direct gap, what stayed unobservable, ethics.

Ethics: self-experiment consent; data stays in the local volume; no actions on third parties;
kill switch; non-self environments (cat, roommate) require consent, supervising human for
physical actions, allow-listed actions, welfare veto.

## Rubric (100)

25 spec v1→v2 with correct direct/proxy tags · 20 taxonomy placement for both phases ·
20 gaming analysis (one concrete behaviour that scores high and hurts hidden state) ·
20 wild memo (no causal claims from n=1; names a confound) · 10 pass@k/pass^k + cost ·
5 traces linked. Zero for quiz-score-only without a miss-analysis.
