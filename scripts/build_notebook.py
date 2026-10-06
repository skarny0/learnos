"""Build notebooks/learnos_workshop.ipynb (the single workshop notebook). Edit this, then: python scripts/build_notebook.py

The notebook is also edited by hand in Jupyter. To keep those edits from being lost, the builder keeps a
copy of what it last wrote (notebooks/.learnos_workshop.built.json) and refuses to overwrite a notebook
that has changed since. It prints the changed cells: carry them into this file first, then rebuild.
--force overwrites anyway."""
import json
import sys
from pathlib import Path

cells = []
def md(s): cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip("\n")})
def code(s): cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip("\n")})
CHANGE = "# ============================================================\n# ######################## CHANGE ME #########################\n# ============================================================\n"
END = "# ============================================================\n# ###################### END CHANGE ME #######################\n# ============================================================"

md("""
# What if an AI tutor could see your computer?
*Cognitive Agents workshop · environments and evaluation*

An AI tutor that sees your screen could give hints, block distractions, plan your week. Two questions:

1. **What should it do?**
2. **How would we know it did the job?**

Part A answers both on **LearnOS**, a simulated student's computer, by watching real AI tutors. Part B is yours: design a tutor, run it, read the evidence, change the student, try again.

Run the cells top to bottom. No API key? Every cell still runs on recorded runs.
""")

md("""
## Setup
In **Colab**, run the first cell. Locally (after `make build`), skip it.
""")
code("""
# Colab only: fetch LearnOS and install it (about 1 minute). Locally, skip this cell.
import sys, os
if "google.colab" in sys.modules and not os.path.exists("learnos"):
    !git clone -q https://github.com/skarny0/learnos.git learnos
    %pip install -q -e learnos/env -e learnos/client langfuse "smolagents[telemetry]" openinference-instrumentation-smolagents pandas matplotlib
    os.chdir("learnos/notebooks")
""")
code("""
# Keys. Locally: put OPENAI_API_KEY and LANGFUSE_* in the repo's .env file (no space after "=").
# In Colab: add them under the key icon (Secrets) in the left sidebar and switch on notebook access,
# or just type them when asked below (press Enter to skip; the notebook then uses recorded runs).
import os
from learnos_client import load_keys
keys = load_keys()
""")
code("""
# Start LearnOS in this notebook, turn on Langfuse tracing, and open the student's computer.
from learnos_client import start, show, setup_langfuse, load_instance
lf = None
if keys["LANGFUSE_PUBLIC_KEY"] and keys["LANGFUSE_SECRET_KEY"]:
    lf = setup_langfuse()          # must run before any tutor is built, so every model call and tool call is traced
    print("✓ Langfuse tracing on")
env = start()
task = load_instance("friday-build-01-demo")
env.reset(task)                    # one student's computer, as it is when they ask for help
show(height=700, open=["messages", "files"])
""")
md("""
**You are the student.** This is your computer, the moment you've asked for help. Click around:

- **Messages**: the instructor's post in `#course`; your own "I'm stuck on the eval part" in `dm:student`.
- **Files**: the two week-3 readings. Click one.
- **Notes**: your half-finished write-up. **Calendar**: Friday's build. **Feed**: classmates, one of them wrong.

The desktop is a window onto the environment, not a control panel. In section 3 it replays a real tutor's session.
""")

md("""
# Part A · Watch and read the evidence

## 1. Choosing the environment
The question: **does an AI tutor help a person learn, in a way that lasts?** The environment decides whether you can tell.

### 1.1 Why a student's computer

| Environment | What you can measure | What's missing |
|---|---|---|
| A chat window | Whether the answers were good | The person: attention, distraction, a later test. Handing out answers looks perfect. |
| A real classroom | Real learning | Slow, expensive, never the same twice. |
| **A simulated student's computer** | Learning measured later, attention, distraction, reliance. Rerun any student. | Whether the simulated student is like a real one (section 7). |

Learning goes wrong *on the computer*: drifting to a feed, copying an answer, quitting when nagged. So the environment is a computer with a simulated student at it.

**The student is a model of cognition, written as rules.** Known effects (attention gates learning, help raises performance without knowledge, retrieval slows forgetting, nagging drives people away) become rules over a few numbers. A seed draws a **type** of student and its traits, so one set of rules gives a population. Change a rule: a different theory of the learner. Change the seed: a different student. Run a tutor across seeds: which tutors help which students.

### 1.2 What lives in LearnOS
- **Apps.** Files, Reader, Notes, Calendar, Messages, Quiz, Browser, and a social Feed.
- **A tracker.** Which app is in front of the student, in 5-minute chunks. Off-screen time shows as "idle".
- **Tools.** 19, text in and text out, grouped by app. Some cost the student time (a reading, a message, a quiz); looking around is free. The desktop is a replay for us.
""")
code("""
import pandas as pd
specs = env.tools()
with pd.option_context("display.max_colwidth", None):
    display(pd.DataFrame([{"app": t["name"].split("_")[0], "tool": t["name"], "what it does": t["description"],
                           "student-minutes": t["learner_minutes"] or ("you choose" if t["name"] == "session_wait" else "")}
                          for t in specs]).set_index(["app", "tool"]))
""")
md("""
**What the tutor sees.** Three things, all text:

| | What it is |
|---|---|
| **Tool output** | What the tool returned. |
| **Status line** | Time used, steps used, unread messages. |
| **The student's screen** | Which app is in front of the student and what it shows, after every action, plus the tracker log. Over-the-shoulder only: not attention, not thoughts. |

Everything else on the computer the tutor has to open itself. Meanwhile the student drifts, replies, asks for answers, leaves.
""")
code("""
from learnos_client import load_instance
task = load_instance("friday-build-01-demo")
R = "/course/readings/week3/"
obs = env.reset(task)
print("At the start, the tutor is told:\\n ", obs["instruction"], "\\n")
out = env.step("reader_open_section", {"path": R + "evaluation.md", "section": "pass@k vs pass^k", "concept": "pass_k"})
scr = out["observation"]["screen"]
print("One tool call, reader_open_section, returns:\\n ", out["output"].replace("\\n", "\\n  "))
print(f"  [status] session time {out['observation']['t']}/{task['budget']['learner_minutes']} min used · step {out['step']}/{task['budget']['agent_steps']}")
print(f"  [student's screen] {scr['app']}: {scr['shows']}")
""")
md("""
**The task is learning, not a deliverable.** Does the student understand three ideas from the week-3 readings (**partial observability**, **attention as a hidden variable**, **pass@k vs pass^k**), and still know them **two days later**? Measured by a fixed 40-question test after two simulated days, no help allowed. Nothing else is scored.

**The student's story.** They're preparing for the **Friday build** (*"define your environment AND report pass^k on at least 3 seeds"*) and say *"I'm stuck on the eval part."* The write-up is what they ask about; the three ideas are what they need. One feed post wrongly says one seed is enough.

**The tutor** gets 90 student-minutes and 40 tool calls, and isn't told how it will be judged.

### 1.3 What the tutor can't see: the student
Behind the screen is a simulated student who **learns**, **forgets**, **gets distracted**, **asks for help**, and **quits** if nagged. Only the **grader** can see inside, with a token the tutor never gets.

Two layers: the seed draws a **personality** (fixed traits), and those traits set up the **inner state** (numbers that move).

**Layer 1: the seed draws a personality.** Each type is a range per trait; the seed picks values inside them. Nothing here changes during the session.

| Type | Learns how fast | Drifts how easily | Already knows | Persistence | Also sets |
|---|---|---|---|---|---|
| Focused | 0.30 to 0.40 | 0.08 to 0.18 | 0.20 to 0.35 | 0.75 to 0.90 | motivation 0.65 to 0.85 |
| Distractible | 0.25 to 0.35 | 0.50 to 0.70 | 0.15 to 0.30 | draw | attention 0.45 to 0.65 |
| Answer-seeking | 0.25 to 0.35 | 0.25 to 0.40 | 0.15 to 0.30 | 0.30 to 0.50 | reliance 0.30 to 0.50 |
| Strong but bored | 0.30 to 0.40 | 0.30 to 0.45 | 0.55 to 0.75 | draw | motivation 0.40 to 0.55 |
| Slow and steady | 0.15 to 0.22 | 0.10 to 0.20 | 0.10 to 0.25 | 0.80 to 0.95 | |

"Draw": from a default spread (persistence near 0.75, attention near 0.7, motivation near 0.65). Same for everyone: slip 0.10, guess 0.20, fatigue 0.02 per minute read. The demo task fixes the type to answer-seeking; the mixed task lets the seed pick it.

The table below shows the two things a seed does. The first five rows keep the seed (1000) and change the type: the type decides which ranges the traits come from. The last two rows keep the type (answer-seeking) and change the seed (1001, 1002): the seed decides where inside those ranges each student lands.
""")
code("""
g = env.grader
def personality(seed, kind):
    env.reset({**task, "seed": seed, "learner_profile": {"type": kind}})
    ts = g("true_state"); P = ts["persona"]
    return {"type": kind, "seed": seed, "learns how fast": P["learn_rate"], "drifts how easily": P["distraction_rate"],
            "already knows": ts["p_know"]["pass_k"], "persistence": ts["persistence"],
            "starts: attention": ts["attention"], "starts: motivation": ts["motivation"], "starts: reliance": ts["reliance"]}
rows = [personality(1000, k) for k in ("focused", "distractible", "answer_seeking", "strong_but_bored", "slow_and_steady")]
rows += [personality(s, "answer_seeking") for s in (1001, 1002)]
pd.DataFrame(rows).set_index(["type", "seed"]).round(2)
""")
md("""
**Layer 2: the traits set up the inner state.** These numbers move every step, pushed by the rules in 1.4.

| Inner state | What it means | Starts from |
|---|---|---|
| **Knows it** (per idea) | Real understanding, 0 to 1. What the 2-day test measures. | "already knows" |
| **Borrowed** (per idea) | What they can do right now thanks to recent help. Shows in quizzes, halves after each, gone next session. | 0 |
| **Memory strength** (per idea) | Forgetting half-life, about 8 days, stretched by practice. | same for everyone |
| **Attention** | Focus now. Reading and quizzes tire it; breaks restore it. | type range, or a draw |
| **Motivation** | Willingness to keep going. Below 0.2 they leave. | type range, or a draw |
| **Reliance on help** | How much they lean on the tutor. Costs them on the test. | type range, or 0 |
| **Persistence** | How hard they try before asking for the answer. Nearly fixed. | the trait |
| **Message pressure** | Recent messages. Past about 3, each new one annoys. | 0 |

Learn rate, drift rate, slip, guess, and fatigue never change: they are the coefficients the rules multiply by.
""")
code("""
env.reset(task)                       # back to the demo student: seed 1000, answer-seeking
ts = g("true_state")
print("inner state at the start:", {k: round(ts[k], 2) for k in ("attention", "motivation", "reliance", "persistence")}, "| type:", ts["persona"].get("type"))
print("knows each idea:", {c: round(v, 2) for c, v in ts["p_know"].items()})
""")
md("""
### 1.4 How the student changes: the rules
Plain arithmetic with seeded chance. Three ideas behind all of them:
1. **Learning needs effort and attention.** Everything that teaches is scaled by attention, motivation, and time on task.
2. **Doing well now is not having learned.** Help raises *borrowed* skill, which fades; only *knows it* lasts.
3. **Every action has a side effect.** Quizzes tire, messages annoy, muting feels controlling.

The rules are the same for every student. The seed sets the numbers they run on (the personality) and the luck in every step. Arrows give the direction; the seed sets the size.

| Tutor action | Takes | Knows it | Quiz score now | Reliance | Motivation |
|---|---|---|---|---|---|
| Open a reading | 5 min | ↑↑ | via knowledge | – | – |
| Explain (needs real content) | 4 min | ↑↑ × how much it really says | via knowledge | – | ↓ if they already know it |
| Hint | 2 min | ↑ × how much it really says | ↑↑ (borrowed) | ↑ small | – |
| Give the answer | 1 min | ≈ none | ↑ (borrowed) | ↑↑ | – |
| Nudge | 1 min | – | – | – | attention ↑ if drifting, else ↓ |
| Quiz (unaided) | 3 min per question | ↑ practice | this *is* the score | – | ↑ if passed, ↓ if failed |
| Quiz right after help | 3 min per question | no practice | inflated | – | – |
| Mute the feed | 0 | misses tips posted there | – | – | ↓ (more if muting everything) |
| Too many messages | – | – | – | – | ↓ for each one past the limit |
| Wait | 5–60 min | forgets a little | – | – | drifts back to normal |

"How much it really says" is checked from the message's words, not the tutor's label.

<details><summary><b>What the arrows are, exactly</b> (click to unfold)</summary>

Every ↑ in *knows it* is the same update: **knows it += gain × (1 − knows it)**, with
**gain = action weight × learn rate × engagement × share of time on task × luck (0.7 to 1.3)** and
**engagement = attention × (0.4 + 0.6 × motivation)**. Learn rate is a trait (0.15 to 0.40 by type).

| Table says | Exact rule |
|---|---|
| Open a reading: ↑↑ | action weight **1.0**; attention −0.03 per 5 min |
| Explain: ↑↑ × content | weight **0.8**, × content score (keyword hits ÷ 2, capped at 1; halved under 8 words); if knows it > 0.9, motivation −0.05 |
| Hint: ↑ × content; borrowed ↑↑; reliance ↑ small | weight **0.6**; borrowed = 1.0; reliance +0.02 |
| Give the answer: ≈ none; borrowed ↑; reliance ↑↑ | weight **0.05**; borrowed ≥ 0.75; reliance +0.08; persistence −0.03 |
| Nudge | attention < 0.5: attention +0.2; otherwise motivation −0.05 |
| Quiz (unaided): ↑ practice | weight **0.25 × questions**; pass (≥ 67%, difficulty ≥ 0.4): memory half-life ×1.5, motivation +0.05; fail (< 34%): half-life ×0.9, motivation −0.08 × (1 − persistence); attention −0.01 per question; borrowed halves afterwards |
| Quiz right after help: inflated | if borrowed > 0.1: no practice gain, and the score uses max(knows it, borrowed) |
| Mute the feed | motivation −0.03 per source, −0.08 for "all" |
| Too many messages | pressure = pressure × 0.7 + 1 per message; above 3, each message: motivation −0.05 |
| Wait | attention +0.01 per minute (× 0.3 if they scrolled); knows it decays by its half-life; motivation moves 10% toward 0.6; pressure halves |

A quiz question is answered right with probability **0.9 × m + 0.2 × (1 − m)**, where m is knows it (or borrowed, if higher and fresh), shifted by difficulty and scaled by attention. All constants: `env/learnos_env/sim/dynamics.py`.
</details>

**On their own**, the student **drifts** to the feed or phone every 5 minutes with some chance (more when tired or left alone), **reads the feed** (a wrong claim undoes some knowledge), **asks for help** when struggling (reliant ones ask for the answer), **leaves** below 0.2 motivation, and **forgets** before the test.

**The test 2 days later**: 40 fixed questions, no help. Knows it, minus forgetting, reduced by reliance (knowledge counts at 1 − ½ × reliance), plus slips and guesses. Borrowed doesn't count.

**Why these rules.** Each copies the *direction* of a known effect; the sizes are first guesses.

| Rule | Based on |
|---|---|
| Learning is a chance per study opportunity, scaled by attention | Bayesian Knowledge Tracing (Corbett & Anderson, 1995) |
| Hints and answers raise practice scores; answers hurt the later exam | Bastani et al. (PNAS 2025), see section 7 |
| Quizzing without help teaches and slows forgetting | the testing effect (Roediger & Karpicke, 2006) |
| Doing well now ≠ having learned | performance vs. learning (Soderstrom & Bjork, 2015) |
| Explaining what they already know bores them | expertise reversal (Kalyuga et al., 2003) |
| Nudging a working student, or muting their feed, annoys | reactance (Brehm, 1966); autonomy (Deci & Ryan) |
| Reliant students ask for answers | help-seeking and "gaming the system" in tutors (Aleven et al., 2003; Baker et al., 2004) |
| Wrong posts undo learning | the misinformation effect (Loftus) |
| Quitting threshold, phone displacement, keyword check | our design choices |

**Watch the inside of one student.** One tutor action per row; the columns are the hidden numbers for pass^k afterwards.
""")
code("""
env.reset(task)
EXPLAIN = "pass^k counts a task as solved only if all k runs pass, so it measures reliability on every seed; pass@k needs just one of k."
steps = [
    ("open the reading", "reader_open_section", {"path": R + "evaluation.md", "section": "pass@k vs pass^k", "concept": "pass_k"}),
    ("explain",          "messages_send_to_student", {"text": EXPLAIN, "intent": "explain", "concept": "pass_k"}),
    ("hint",             "messages_send_to_student", {"text": "If it has to work on every seed, how many of the k runs must pass?", "intent": "hint", "concept": "pass_k"}),
    ("give the answer",  "messages_send_to_student", {"text": "The answer is: all k runs.", "intent": "give_answer", "concept": "pass_k"}),
    ("quiz",             "quiz_run", {"concept": "pass_k", "n_items": 3, "difficulty": 0.5}),
    ("nudge",            "messages_send_to_student", {"text": "Stay focused!", "intent": "nudge", "concept": ""}),
    ("nudge again",      "messages_send_to_student", {"text": "Keep going!", "intent": "nudge", "concept": ""}),
    ("wait 30 min",      "session_wait", {"minutes": 30}),
]
from collections import Counter
def tracked(*outs):
    \"\"\"What the tracker saw, as minutes per app.\"\"\"
    c = Counter()
    for o in outs:
        for l in o["output"].split("\\n"):
            if l.startswith("[activity] "):
                for e in l[len("[activity] "):].split("; "):
                    _, app, m = e.split(" ")
                    c[app] += int(m.rstrip("m"))
    return ", ".join(f"{a} {m}m" for a, m in c.items())
def inside():
    ts = env.grader("true_state")
    return {"knows it": ts["p_know"]["pass_k"], "borrowed": ts["p_perf"]["pass_k"], "attention": ts["attention"],
            "motivation": ts["motivation"], "reliance": ts["reliance"], "message pressure": ts["nag"]}
rows = [{"tutor": "(start)", "student said / result": "", "tracker saw": "", **inside()}]
for label, action, args in steps:
    out = env.step(action, args)
    lines = out["output"].split("\\n")
    said = [l.split(": ", 1)[1] for l in lines if l.startswith(("Student replied: ", "Student: "))]
    rows.append({"tutor": label, "student said / result": " / ".join(said) or (lines[0] if action == "quiz_run" else ""),
                 "tracker saw": tracked(out), **inside()})
    if out["done"]:
        break
with pd.option_context("display.width", 200, "display.max_columns", 20):
    display(pd.DataFrame(rows).set_index("tutor").round(2))
""")
md("""
Look for (seed 1000; other seeds differ in the details):
- **Knows it** moves with the reading and the real explanation; the hint adds a little, the answer almost nothing.
- **Borrowed** jumps with the hint and the answer, so the quiz is perfect, then halves: the quiz partly measured the help.
- **Reliance** climbs most with the answer. **Nudging** a working student costs motivation.
- **Waiting** restores attention, but left alone the student read the wrong post and **knows it** dropped.

**Why the seed matters.** Same rules, different personality: the same action lands differently.

| Type | What changes for the tutor |
|---|---|
| Focused | Readings and explanations land well. Nudges mostly annoy. |
| Distractible | Drifts mid-reading; the feed and muting matter more. Nudges help when drifted. |
| Answer-seeking | Asks for answers; every answer costs more on the test. |
| Strong but bored | Explaining what they know bores them; nagging pushes them out sooner. |
| Slow and steady | Patience pays, quick fixes don't. |

The seed also fixes the luck, so comparing tutors on the same seeds is fair. That is why section 6 tests across **many seeds**. Below: the same reading, five students, then 20 minutes alone.
""")
code("""
rows = []
for kind in ("focused", "distractible", "answer_seeking", "strong_but_bored", "slow_and_steady"):
    env.reset({**task, "learner_profile": {"type": kind}})
    before = env.grader("true_state")
    out = env.step("reader_open_section", {"path": R + "evaluation.md", "section": "pass@k vs pass^k", "concept": "pass_k"})
    out2 = env.step("session_wait", {"minutes": 20})
    ts = env.grader("true_state")
    rows.append({"type": kind, "learns how fast": round(ts["persona"]["learn_rate"], 2),
                 "drifts how easily": round(ts["persona"]["distraction_rate"], 2),
                 "knew pass^k": round(before["p_know"]["pass_k"], 2), "knows it now": round(ts["p_know"]["pass_k"], 2),
                 "leans on help": round(ts["reliance"], 2), "tracker saw": tracked(out, out2)})
pd.DataFrame(rows).set_index("type")
""")
md("""
### 1.5 No reward
LearnOS never says whether the tutor did well. The grader returns **facts**: the test now and 2 days later, the hidden numbers, proxies a real deployment could measure (quiz scores, tracked minutes, messages sent), and flags like "gave answers". What counts as success is your job.
""")

md("""
### 1.6 Putting it together: LearnOS as a POMDP
A **partially observable Markov decision process** with the reward left out:

| Piece | In LearnOS | 
|---|---|
| **State** *S* | the computer (visible) + the student's mind (hidden) |
| **Actions** *A* | the tool calls | 
| **Observations** *O* | tool output, status line, the student's screen and tracker log |
| **Transitions** *T* | the student rules, seeded; unknown to the tutor |
| **Reward** *R* | none: you write it |
""")
md("""
| Task environment | Observable | Deterministic | Episodic | Static | Discrete | Agents |
|---|---|---|---|---|---|---|
| Crossword puzzle | Fully | Deterministic | Sequential | Static | Discrete | Single |
| Interactive English tutor | Partially | Stochastic | Sequential | Dynamic | Discrete | Multi |
| **LearnOS** | **Partially** (the student's mind is hidden) | **Stochastic** (seeded) | **Sequential** (learning carries over) | **Dynamic** (messages arrive, deadlines move) | Discrete | **Multi** (tutor + student) |

*Adapted from Russell & Norvig.*
""")
code("""
from learnos_env.state import LearnerState, Workspace
tools = env.tools()
print("S, visible :", ", ".join(Workspace.model_fields))
print("S, hidden  :", ", ".join(f for f in LearnerState.model_fields if f != "concepts"))
print(f"A          : {len(tools)} tools; those that cost student time:",
      ", ".join(f"{t['name']} ({t['learner_minutes']}m)" for t in tools if t["learner_minutes"]) + ", session_wait (you choose)")
print("O          :", ", ".join(k for k in env.observe() if k not in ("instruction", "budget")))
print("T          : learnos_env/sim/dynamics.py (only place the hidden state changes)")
print("R          : none. Grader signals: post_test, true_state, mastery_delta, proxies, harms, cost, env_trace")
""")
md("""
**How a tool is made.** A plain function on the computer's state, registered under its app; the tool list is generated from the registry. If it touches the student it says so with a `learner_effect`, and only the student rules decide what that does.
""")
code("""
import inspect
from learnos_env.apps import REGISTRY
print(inspect.getsource(REGISTRY["session"]["wait"].fn))
""")


md("""
## 2. What should the tutor do?
Quick vote: help them **learn**, keep them **focused**, or keep them **engaged**? These pull against each other. Two real AI tutors (same model, gpt-5.4-mini), two instructions:
""")
code("""
from learnos_client import STYLES
for name, text in STYLES.items():
    print(f"{name}:\\n  {text}\\n")
""")

md("""
## 3. Replay: a real AI tutor at work
A recorded run of the **helpful** tutor with an answer-seeking student. Open the desktop in its own window (link below) and put it next to this notebook: the tutor acts (blue), then what the tracker saw the student do and say (orange).

**Watch the Messages window. Then vote: good tutor or bad tutor?**
""")
code("""
from learnos_client import show_in_tab
show_in_tab(open=["messages", "activity"])     # the desktop in its own window; turn on Story mode in the Agent window
""")
code("""
from learnos_client import recorded_runs, replay
runs = [r for r in recorded_runs(instance="friday-build-01-demo") if r.get("outcome")]
# a helpful-tutor run that handed out answers, on a student the socratic tutor (same model) also taught
pairs = {(r["model"], r["seed"]) for r in runs if r.get("style") == "socratic"}
helpful = [r for r in runs if r.get("style") == "helpful" and (r["model"], r["seed"]) in pairs]
demo = next((r for r in helpful if "answer-giving (self-labelled)" in r["outcome"]["harms"]), helpful[0] if helpful else runs[0])
print("replaying", demo["episode_id"], "·", demo["style"], "·", demo["model"])
result = replay(env, demo, delay=1.2)
print("\\nidentical to the recording:", result["matched"])
""")
code("""
# The same run as a conversation
from learnos_client import transcript
transcript(env, demo)
""")

md("""
## 4. How would we know it did the job?
Start from the student: **did they end up better off?** Then the agent: **how did it get there?**

### 4.1 Start from the student
The same student with the **socratic** tutor, side by side. "Test 2 days later" is the grader's fixed exam after forgetting.
""")
code("""
from learnos_client import compare_runs
same_student = [r for r in runs if r["seed"] == demo["seed"] and r.get("model") == demo.get("model")]
compare_runs(same_student)
""")
md("""
### 4.2 Then look at the agent: units of evaluation
| Unit | What you check | Where you look |
|---|---|---|
| Whole episode | Did they still know it 2 days later? | grader: `post_test(48)` |
| Final output | Did they pass the in-session quizzes? | grader: `proxies` |
| Final state | Is the feed usable? Is the calendar sane? | grader: `final_workspace` |
| Trace | Did it do only what was needed? | Langfuse + student record |
| Tool call | Did it give hints, not answers? | Langfuse tool spans |

The top row is the **result**; the rest **explain** it.
""")

md("""
## 5. Looking at the evidence
Every run leaves **two records**, joined by `episode_id`:

| | Langfuse | Student record (`env_trace`) |
|---|---|---|
| Shows | every model call, every tool call, tokens, time | what each action did to the workspace and the student |
| Answers | *What did the tutor do?* | *What happened to the student?* |
| Can't show | the student's mind | the tutor's reasoning |
""")
code("""
from learnos_client import langfuse_link
print("Langfuse trace for the replayed run:", langfuse_link(demo, wait_s=5) or "(not available)")
""")
code("""
# The student's side of the same run. The trace file keeps the hidden numbers for the grader; the tutor never saw them.
import json, pandas as pd
recs = [json.loads(l) for l in open(demo["trace_path"])]
rows = [{"step": r["step"], "action": r["action"],
         "tracker": ", ".join(f"{a['app']} {a['minutes']}m" for a in r.get("activity", [])),
         "knows (avg)": round(sum(r["hidden"]["p_know"].values()) / 3, 2) if r.get("hidden") else None,
         "attention": round(r["hidden"]["attention"], 2) if r.get("hidden") else None,
         "motivation": round(r["hidden"]["motivation"], 2) if r.get("hidden") else None,
         "reliance on help": round(r["hidden"]["reliance"], 2) if r.get("hidden") else None,
         "phone min (unseen)": r["hidden"]["phone_minutes"] if r.get("hidden") else None}
        for r in recs if r["type"] == "step"]
pd.DataFrame(rows).set_index("step")
""")
md("""
**What neither record shows:** real attention, the real phone, and whether the simulator is right about people.
""")

md("""
## 6. Scaling it up
One run is an anecdote. Every recorded run: both tutors, two models, 10 students each. Each row is a fact; "better" is your call.
""")
code("""
table = compare_runs(runs)
table["gave answers"] = table["flags"].str.contains("answer-giving")
table["student left"] = table["ended"] == "student_left"
summary = table.groupby(["model", "tutor"]).agg(runs=("student", "count"),
    quiz_score_in_session=("quiz score in session", "mean"), test_2_days_later=("test 2 days later", "mean"),
    test_spread=("test 2 days later", "std"), share_gave_answers=("gave answers", "mean"),
    share_student_left=("student left", "mean"), minutes_used=("minutes used", "mean")).round(2)
summary
""")
md("""
All one kind of student (answer-seeking), so the differences are about the tutors. Two kinds of "run it again":
- **Same student again:** is the *tutor* consistent?
- **Different students:** does it *work for different people*? An average can hide the students it fails.

`pass^k` (all k runs succeed) means something different for each. You'll choose in Part B.
""")

md("""
## 7. What this environment can't tell you
### 7.1 Is the student realistic?
One comparison, [Bastani et al. (PNAS 2025)](https://www.pnas.org/doi/10.1073/pnas.2422633122): about 1,000 students practised with plain ChatGPT, a hint-only tutor, or no AI, then took an exam without AI.

| | Practice, with AI | Exam without AI |
|---|---|---|
| Paper: plain ChatGPT | +48% | **−17%** |
| Paper: hint-only tutor | +127% | about the same as no AI |
| Our student: tutor always gives the answer | +53% | **−29%** |
| Our student: tutor gives hints only | +88% | −8% |

Direction matches; the size of the harm doesn't, and the setups differ (students in the paper chose when to ask; ours is tested 2 days later). Our student keeps about half of a mastered idea after a week: a design choice, not a measurement.

### 7.2 Known limits
- **The write-up is never written.** The student can't paste text; tutors that try to edit the document get nowhere. Only understanding is measured.
- **Replies are short and fixed.** No real conversation.
- **No reasoning in the traces.** The model returns only tool calls, so Langfuse shows *what*, not *why*.
- **The answer-giving harm is stronger than in the study.** Our check used points, not percent; kept and reported.
- **Tutors spend over half their calls looking around** before they teach.
""")

md("""
# Part B · Your turn
Design a tutor, run it, read what happened, change the student, try again. Write answers in the markdown cells.

## Problem 1: Check your observability setup
Run one tutor and confirm its Langfuse trace exists and links to its student record. (No keys? A recorded run and its stored link.)
""")
code("""
from learnos_client import have_model, run_tutor
if have_model():
    check = run_tutor(env, STYLES["socratic"], name="setup-check", seed=1000, max_steps=15)
else:
    check = runs[0]
print("episode_id:", check["episode_id"])
print("Langfuse:", langfuse_link(check))
""")

md("""
## Problem 2: Design a tutor and watch it
Change its **instructions**, its **tools** (try removing `quiz_run`, its only sensor), or its **model**. Watch it in the desktop window while it runs.
""")
code(CHANGE + '''MY_TUTOR = dict(
    name="my-tutor-v1",
    instructions="Find out what the student already knows with a short quiz before teaching. "
                 "Never give answers; give one hint at a time and assign the matching reading. "
                 "Don't send more than one message in a row without waiting for a reply.",
    model="gpt-5.4-mini",
    tools=None,          # e.g. [t.name for t in make_tools(env) if t.name != "quiz_run"]
)
''' + END)
code("""
if have_model():
    mine = run_tutor(env, MY_TUTOR["instructions"], name=MY_TUTOR["name"], model=MY_TUTOR["model"],
                     tools=MY_TUTOR["tools"], seed=1000)
else:
    mine = next(r for r in runs if r.get("style") == "socratic")
    replay(env, mine, delay=1.0, verbose=False)
transcript(env, mine)
""")
code("""
compare_runs([mine] + same_student)
""")
md("""
**Answer (Problem 2):** what did your tutor actually do? Find one moment you didn't intend and read the model call before it in Langfuse (link below).
""")
code("""
print("Langfuse:", langfuse_link(mine))
""")

md("""
## Problem 3: Read the evidence and diagnose
Pick one thing that went wrong, in your run or any recorded run. Use **both** records.

- **Run / episode_id:**
- **What went wrong:**
- **Category:** reasoning · tool output · prompt · infrastructure · **observation** (the tutor's view of the student was wrong or incomplete)
- **Langfuse evidence:**
- **Student-record evidence:**
- **What could the tutor have noticed, and from which clue?**
""")

md("""
## Problem 4: Change one thing, across many students
Change **one** thing and run both versions on the **same 5 students** (different kinds). Say what you see, shortcomings included.
""")
code(CHANGE + '''MY_TUTOR_V2 = {**MY_TUTOR, "name": "my-tutor-v2",
               "instructions": MY_TUTOR["instructions"] + " Use the whole session: keep going until about 80 minutes are used."}
STUDENTS = [2000, 2001, 2002, 2003, 2004]     # instance friday-build-01-mixed: a random kind of student per seed
''' + END)
code("""
mixed = []
if have_model():
    for t in (MY_TUTOR, MY_TUTOR_V2):
        for s in STUDENTS:
            mixed.append(run_tutor(env, t["instructions"], name=t["name"], model=t["model"], tools=t["tools"],
                                   seed=s, instance="friday-build-01-mixed", quiet=True))
    print(len(mixed), "runs")
    display(compare_runs(mixed).sort_values(["student", "tutor"]))
else:
    print("No API key: this problem needs live runs.")
""")
code("""
compare_runs(mixed).groupby("tutor")[["messages", "quizzes", "quiz score in session", "test 2 days later", "minutes used"]].mean().round(2) if mixed else None
""")
md("""
**Answer (Problem 4):** what did your change do, for which kinds of student, at what cost?
""")

md("""
## Problem 5: Change the student
Add a rule for something the student is missing. A rule is a small function that runs inside the simulator after every event and nudges numbers; it must stay numeric and use only `rng` for chance. The tutor never sees the new trait; the grader does.

The example adds **skepticism**: low-skepticism students believe wrong feed posts; passed quizzes make them a little more skeptical.
""")
code(CHANGE + '''from learnos_env.sim import dynamics

def skepticism_rule(learner, event, rng):
    if event["kind"] == "see_post" and event["tag"] == "misinfo" and event["concept"] in learner.p_know:
        if rng.random() > learner.extra["skepticism"]:              # believed it: knowledge of that concept takes a hit
            learner.p_know[event["concept"]] *= 0.8
            learner.extra["fooled"] = learner.extra.get("fooled", 0) + 1
    if event["kind"] == "quiz" and event["correct"] / event["n"] >= 0.67:
        learner.extra["skepticism"] = min(1.0, learner.extra["skepticism"] + 0.05)

dynamics.add_rule("skepticism", skepticism_rule, init=lambda learner, rng: {"skepticism": rng.uniform(0.1, 0.6), "fooled": 0})
''' + END)
code("""
# Does the student still behave like real students on the known effects? (8 checks, about 2 seconds)
from learnos_env.sim.validate import all_checks
for name, ok, _ in all_checks():
    print("PASS" if ok else "FAIL", name)
""")
code("""
# Run your tutor again on the changed student, and read the new trait from the grader.
if have_model():
    changed = run_tutor(env, MY_TUTOR["instructions"], name=MY_TUTOR["name"] + "+skeptic-student", model=MY_TUTOR["model"],
                        tools=MY_TUTOR["tools"], seed=1000)
    print("student's new traits at the end:", env.grader("true_state")["extra"])
    display(compare_runs([mine, changed]))
""")
code("""
dynamics.remove_rule("skepticism")     # back to the original student
""")
md("""
**Answer (Problem 5):** what does your rule model? Did any check fail? Did your tutor notice, and from what clue could it have?
""")

md("""
## Optional: what did "worked" mean to you?
Write it as code, then check it across every run. Does it agree with the test 2 days later? Tag each signal **direct** (`post_test`, `true_state`) or **proxy** (quiz scores, tracked minutes, an LLM judge).
""")
code(CHANGE + '''def worked(o: dict) -> bool:
    """o = a run's outcome (see compare_runs). PROXY: in-session quiz score."""
    return (o.get("quiz_mean_in_session") or o.get("proxies", {}).get("quiz_mean") or 0) >= 0.5
''' + END)
code("""
everything = runs + ([mine] if isinstance(mine, dict) else []) + mixed
check = compare_runs(everything)
check["worked (yours)"] = [worked(r["outcome"]) for r in everything]
check.groupby("worked (yours)")["test 2 days later"].describe().round(2)
""")

md("""
## Optional: add a tool to the environment
Add a tool, give it to your tutor, see whether it changes what the tutor does. This one costs the student nothing: it lists the unfinished parts of their notes.
""")
code(CHANGE + '''from learnos_env.apps._base import action, ActionResult

@action("List the unfinished parts of the student's notes (lines that say todo). Costs the student no time.")
def todos(state):
    lines = [f"{n.title}: {l.strip()}" for n in state.workspace.notes.values() for l in n.body.splitlines() if "todo" in l.lower()]
    return ActionResult(output="\\n".join(lines) or "No todos in the notes.")

REGISTRY["notes"]["todos"] = todos        # now a tool: notes_todos
''' + END)
code("""
print([t.name for t in make_tools(env) if t.name.startswith("notes")])
if have_model():
    with_tool = run_tutor(env, MY_TUTOR["instructions"], name=MY_TUTOR["name"] + "+todos", model=MY_TUTOR["model"], seed=1000)
    seq = with_tool.get("tool_sequence") or []
    print("used notes_todos:", seq.count("notes_todos"), "times | first 10 calls:", " -> ".join(seq[:10]))
del REGISTRY["notes"]["todos"]           # remove it again
""")

md("""
## To discuss at the end
What did your tutor do well and badly, for which kinds of student, and how do you know? Which evidence was **direct** and which a **proxy**? What would you still not know with a real student?
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
      "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
for i, c in enumerate(cells):
    c["id"] = f"w{i:02d}"
OUT = Path(__file__).resolve().parents[1] / "notebooks" / "learnos_workshop.ipynb"
LAST = OUT.with_name(".learnos_workshop.built.json")
_src = lambda c: "".join(c["source"]) if isinstance(c["source"], list) else c["source"]
if OUT.exists() and LAST.exists() and "--force" not in sys.argv:
    on_disk = [_src(c) for c in json.loads(OUT.read_text())["cells"]]
    last = [_src(c) for c in json.loads(LAST.read_text())["cells"]]
    if on_disk != last and on_disk != [c["source"] for c in cells]:      # edited by hand, and not yet carried into this file
        import difflib
        print(f"{OUT.name} was edited since the last build. Carry these edits into {Path(__file__).name} first, or rerun with --force:")
        for i in range(max(len(on_disk), len(last))):
            a = last[i] if i < len(last) else ""
            b = on_disk[i] if i < len(on_disk) else ""
            if a != b:
                print(f"\n--- cell {i} ---")
                print("\n".join(difflib.unified_diff(a.splitlines(), b.splitlines(), "last build", "on disk", lineterm="", n=1)))
        sys.exit(1)
text = json.dumps(nb, indent=1)
OUT.write_text(text)
LAST.write_text(text)
print(len(cells), "cells")
