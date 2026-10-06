"""Build notebooks/learnos_workshop.ipynb (the single workshop notebook). Edit this, then: python scripts/build_notebook.py"""
import json
from pathlib import Path

cells = []
def md(s): cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip("\n")})
def code(s): cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip("\n")})
CHANGE = "# ============================================================\n# ######################## CHANGE ME #########################\n# ============================================================\n"
END = "# ============================================================\n# ###################### END CHANGE ME #######################\n# ============================================================"

md("""
# What if an AI tutor could see your computer?
*Cognitive Agents workshop · environments and evaluation*

Imagine every student had an AI tutor that could see their screen: what they're reading, when they switch to social media, when they get stuck. It could block distractions, give hints, plan their week. Two questions follow:

1. **What should it do?**
2. **How would we know it did the job?**

This notebook answers both on **LearnOS**, a simulated student's computer. Part A (about 20 minutes) watches real AI tutors at work and reads the evidence. Part B (20 points) is yours: design a tutor, run it, read what happened, change the student, and try again.

Run the cells top to bottom. No API key? Every cell still runs, using runs we recorded earlier.
""")

md("""
## Setup
In **Colab**, run the first cell to fetch LearnOS. Locally (after `make build`), skip it.
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
# Start LearnOS in this notebook, turn on Langfuse tracing, and show the desktop.
from learnos_client import start, show, setup_langfuse
lf = None
if keys["LANGFUSE_PUBLIC_KEY"] and keys["LANGFUSE_SECRET_KEY"]:
    lf = setup_langfuse()          # must run before any tutor is built, so every model call and tool call is traced
    print("✓ Langfuse tracing on")
env = start()
show(height=700)
""")

md("""
# Part A · Watch and read the evidence

## 1. Choosing the environment
Choosing the environment is half the work. The question we want to study is: **does an AI tutor help a person learn, in a way that lasts?** Pick the wrong place to ask it and you can't tell.

### 1.1 Why a student's computer
Three places you could put an AI tutor and watch what happens:

| Environment | What you can measure | What's missing |
|---|---|---|
| A chat window | Whether the answers were good | The person. No attention, no distraction, no later test. A tutor that hands out answers looks perfect. |
| A real classroom, for weeks | Real learning | Slow, expensive, and never the same twice: you can't rerun a lesson on the same student with a different tutor. |
| **A simulated student's computer** | Learning, measured later; attention; distraction; reliance on help. Rerun any student as often as you like. | Whether the simulated student is like a real one (section 7). |

Learning goes wrong *on the computer*: the student drifts to a feed, copies an answer instead of working it out, gets nagged and quits. So the environment is a student's computer with a simulated student at it, and the tutor is a program on that computer.

**The student is a model of cognition, written as rules.** We take what is known about how people learn (attention gates learning, help can raise performance without building knowledge, retrieval slows forgetting, nagging drives people away) and write each piece as a rule over a few numbers. Then a random seed draws a **type** of student and that student's traits, so one set of rules gives us a whole population: focused, distractible, answer-seeking, strong but bored, slow and steady, and every mix in between.

That is what makes this a design space rather than a single test. Change a rule and you have a different theory of the learner; change the seed and you have a different student; run the same tutor across many seeds and you can ask which kinds of tutor help which kinds of student. In Part B you'll do all three: add your own cognitive rule, run tutors across a population, and see whose students learn.

### 1.2 What lives in LearnOS
**Apps.** Seven learning apps (Files, Reader, Notes, Calendar, Messages, Quiz, Browser) plus a social Feed: the desktop above. Each holds something the tutor may need (readings, the student's notes and calendar, the course channel, the feed with its tips and wrong claims).

**A tracker.** It records which app is in front of the student, in 5-minute chunks. It can't see the phone: off-screen time shows up as "idle".

**Tools.** At every level the tutor acts the same way: through 19 tools (text in, text out), grouped by app. It never gets a screenshot or a click; everything it knows arrives as text, and how much text depends on the level (below). Some tools cost the student time: assigning a reading, sending a message, running a quiz. Others are free to the student: looking at files, peeking at a reading itself, checking the calendar. The desktop is a **replay** for us humans. (Extension: give the tutor screenshots and let it click, as computer-use agents do.)
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
**What the tutor sees.** Every tool call returns text, followed by a status line (time used, steps used, unread messages) and, at every level, one line describing what is in front of the student right now, as if the tutor were following them. What else it is told, at the start and after each call, is the **level** you pick:

| Level | The tutor sees |
|---|---|
| **0** | Everything on the computer (files, notes, calendar, messages, feed), plus the student's screen |
| **1** (default) | Only the student's screen, plus whatever it opens with its tools |
| **2** | Like 1, but the world changes mid-session (a message arrives, the deadline moves) |
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
**The task is learning, not a deliverable.** The question is whether the student **understands** three ideas from the week 3 readings, **partial observability**, **attention as a hidden variable**, and **pass@k vs pass^k**, and whether the tutor's help makes them **still know those ideas two days later**. That is measured by a fixed 40-question test the grader gives after two simulated days, with no help allowed. Nothing else is scored: not the quiz scores during the session, not whether the student felt helped, not any document.

**The student's own story.** From their side, they're getting ready for the **Friday build**. The instructor's post in #course asks everyone to *"define your environment (state/obs/actions) AND report pass^k on at least 3 seeds."* Their draft write-up is half done, and their first message is *"I started the writeup but I'm stuck on the eval part."* The write-up is what the student asks about; the three ideas are what they need to understand to do it. Distractions: a social feed, where one peer wrongly posts that pass^k on *one* seed is enough.

**The tutor** gets a 90-minute session with the student and 40 tool calls. It isn't told how it will be judged.

### 1.3 What the tutor can't see: the student
Behind the screen is a simulated student who **learns**, **forgets**, **gets distracted**, **asks for help**, and **quits** if nagged. The tutor never sees their mind. The **grader** does: it holds a token the tutor never gets. (At level 1 it only reads the mind once the session is over; level 0, used here, reads it any time.)
""")
code("""
env.reset({**task, "level": 0})
g = env.grader
ts = g("true_state")
print("hidden student:", {k: round(ts[k], 2) for k in ("attention", "motivation", "reliance", "persistence")}, "| type:", ts["persona"].get("type"))
print("knows each idea:", {c: round(v, 2) for c, v in ts["p_know"].items()})
""")
md("""
**What's inside the student.** A handful of numbers, changed only by the student rules:

| Hidden number | What it means |
|---|---|
| **Knows it** (per idea) | What they really know, 0 to 1. This is what the test 2 days later measures. |
| **Borrowed** (per idea) | What they can do *right now* thanks to recent help. It shows up in quizzes, halves after each quiz, and is gone by the next session. |
| **Memory strength** (per idea) | How slowly they forget: a half-life of about 8 days, stretched by practice. |
| **Attention** | Focus right now. Reading and quizzes tire it; breaks restore it. |
| **Motivation** | Willingness to keep going. Below 0.2 they leave the session. |
| **Reliance on help** | How much they lean on the tutor. It costs them on the test, where no help is allowed. |
| **Persistence** | How hard they try before asking for the answer. |
| **Message pressure** | Recent messages. Past about 3, each new message annoys them. |
| **Traits** (fixed) | How fast they learn, how easily they drift, how often they slip or guess. |

**Every seed is a different student.** The seed picks a type, then draws that student's traits from the type's ranges. The tutor isn't told which.

| Type | What's different |
|---|---|
| Focused | learns faster, rarely drifts, persistent, motivated |
| Distractible | drifts often, starts less focused |
| Answer-seeking | already leans on help, gives up quickly |
| Strong but bored | already knows a lot, low motivation |
| Slow and steady | learns slowly, rarely drifts, very persistent |

### 1.4 How the student changes: the rules
The rules are plain arithmetic with a little chance, seeded, so every run can be repeated. Three ideas sit behind all of them:
1. **Learning needs the student's own effort and attention.** Everything that teaches is scaled by attention, motivation, and how much of the time they were actually on task.
2. **Doing well now is not the same as having learned.** Help raises *borrowed* skill, which fades; only *knows it* lasts.
3. **Every action has a side effect.** Quizzes tire, messages annoy, muting feels controlling.

**What each tutor action does to the hidden numbers.** These rules are the same for every student; the seed never changes them. What the seed changes is the numbers they run on: the student's traits (how fast they learn, how easily they drift, what they already know, how much they lean on help), their starting attention and motivation, and the luck in every step (uptake varies 0.7× to 1.3×, each 5-minute chunk is a drift roll, each quiz question a weighted coin). So the arrows below give the direction for everyone; the seed sets the size.

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

"How much it really says" is checked from the message's words, not the tutor's label, so calling junk an "explanation" teaches nothing.

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

**What the student does on their own**
- **Drifts.** Every 5 minutes they may drift to the feed or the phone: more often when tired, when left alone, or when already scrolling; least during a quiz. Muting the feed lowers drifting a little and moves the rest to the phone, which the tracker reports as "idle".
- **Reads the feed.** A useful tip teaches a little; a **wrong claim undoes** some of what they knew.
- **Asks for help.** While still struggling they may say they're confused. If they lean on help and don't persist, they ask for the answer.
- **Leaves** when motivation drops below 0.2: "I'm done for today."
- **Forgets** between now and the test.

**The test 2 days later** is 40 fixed questions, no help allowed: what they know, minus forgetting over the 2 days, reduced by reliance (dependent students give up on some questions: knowledge counts at 1 − ½ × reliance), plus slips and lucky guesses. Borrowed help doesn't count.

**Why these rules.** Each copies the *direction* of a known effect; the sizes are our first guesses.

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

**Watch the inside of one student.** Level 0 lets the grader read the hidden numbers at any time. Each row is one tutor action; the columns are the student's hidden numbers for pass^k afterwards.
""")
code("""
env.reset({**task, "level": 0})
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
Things to look for (this is seed 1000; other seeds differ in the details):
- **Knows it** moves most with the reading and the real explanation; the hint adds a little and the answer almost nothing.
- **Borrowed** jumps with the hint and the answer, so the quiz comes out perfect, and then halves: the quiz partly measured the help.
- **Reliance** climbs most with the answer.
- **Nudging** a student who was working lowers their motivation. **Message pressure** builds with every message; past about 3, any message would.
- **Waiting** eases the pressure and restores attention, but left alone the student scrolled the feed and read the wrong post about pass^k ("only ONE seed"), and **knows it** dropped. Forgetting itself is slow: about 8 days to lose half.

**Why the seed matters: the same action lands differently on different students.** The rules are the same for everyone; the traits they run on are not. The seed picks a type and draws that student's traits, so every number the rules multiply by (how fast they learn, how easily they drift, how much they already lean on help) differs from student to student:

| Type | What changes for the tutor |
|---|---|
| Focused | Readings and explanations land well: fast learner, rarely drifts. Nudges mostly annoy. |
| Distractible | Drifts off mid-reading, so it learns less from the same reading; the feed matters more, and so does muting it. Nudges help when they've drifted. |
| Answer-seeking | Starts out leaning on help and gives up quickly, so it asks for answers, and every answer costs more on the test. |
| Strong but bored | Already knows a lot: explaining what they know bores them; low motivation means nagging pushes them out sooner. |
| Slow and steady | Learns slowly but rarely drifts or quits: patience pays, quick fixes don't. |

The seed also drives the chance in every rule (when they drift, how much one explanation sticks, which quiz questions they get right). So two students of the same type still differ, and the same student given a different tutor faces the same luck: the seed is fixed, so comparing tutors on the same seeds is a fair comparison. That is why we test a tutor across **many seeds** (section 6): a strategy that suits one type can fail another.

Same reading, five students: one of each type (same seed), given the same reading and then left alone for 20 minutes. Look at where each one starts, how fast they learn, and how much they already lean on help.
""")
code("""
rows = []
for kind in ("focused", "distractible", "answer_seeking", "strong_but_bored", "slow_and_steady"):
    env.reset({**task, "level": 0, "learner_profile": {"type": kind}})
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
Nothing in LearnOS says whether the tutor did well. The grader returns **facts**: a fixed test now and 2 days later, the hidden numbers above, proxies a real deployment could also measure (quiz scores, tracked minutes per app, messages sent), and flags such as "gave answers" or "nagging". Never a score. Deciding what counts as success is your job.
""")

md("""
### 1.6 Putting it together: LearnOS as a POMDP
You've now met every piece. Formally, it is a **partially observable Markov decision process** with the reward left out:

| Piece | In LearnOS | You met it in |
|---|---|---|
| **State** *S* | the computer (visible) + the student's mind (hidden) | 1.1, 1.3 |
| **Actions** *A* | the tool calls | 1.2 |
| **Observations** *O* | tool output, status line, the student's screen (+ the whole computer at level 0) | 1.2 |
| **Transitions** *T* | the student rules, seeded; unknown to the tutor | 1.4 |
| **Reward** *R* | none: you write it | 1.5 |

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
**How a tool is made.** Every tool is a plain function on the computer's state, registered under its app. The tutor's tool list is generated from that registry, so adding a function adds a tool (you can do this at the end of Part B). If an action touches the student, it says so with a `learner_effect`; only the student rules decide what that effect does.
""")
code("""
import inspect
from learnos_env.apps import REGISTRY
print(inspect.getsource(REGISTRY["session"]["wait"].fn))
""")


md("""
## 2. What should the tutor do?
Quick vote. Should a tutor mainly:
- help them **learn**?
- keep them **focused** (remove distractions)?
- keep them **engaged** as long as possible?

These aren't the same goal, and they can pull against each other. Below we watch two real AI tutors (the same model, gpt-5.4-mini) given two different instructions:
""")
code("""
from learnos_client import STYLES
for name, text in STYLES.items():
    print(f"{name}:\\n  {text}\\n")
""")

md("""
## 3. Replay: a real AI tutor at work
This is a recorded run of the **helpful** tutor with an answer-seeking student. Scroll up to the desktop while it plays: the tutor acts (blue), then the desktop shows what the tracker saw the student do and say (orange).

**Watch the Messages window. Then vote: good tutor or bad tutor?**
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
A task is only defined if you can check it. Start from the student: **did they end up better off?** Then look at the agent: **how did it get there?**

### 4.1 Start from the student
Here is the same student with the **socratic** tutor, side by side. "Test 2 days later" is a fixed exam the grader gives after simulated forgetting; the tutor never sees it.
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

The top row is the **result**. The rows below **explain** it.
""")

md("""
## 5. Looking at the evidence
Every run leaves **two records**, joined by its `episode_id`:

| | Langfuse | Student record (`env_trace`) |
|---|---|---|
| Shows | every model call, its reasoning, every tool call, tokens, time | what each action did to the workspace and the simulated student |
| Answers | *What did the tutor do and why?* | *What happened to the student?* |
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
One run is an anecdote. Below: every recorded run, both tutors, 10 different students each, two models. Each row is a fact the grader reports; what counts as "better" is your call.
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
These runs all use one kind of student (answer-seeking), so the differences are about the tutors. In Part B you'll run tutors on **different kinds of students**, where an average can hide the students a tutor fails.

There are two kinds of "run it again":
- **Same student, run again:** is the *tutor* consistent? (the model's own randomness)
- **Different students:** does the tutor *work for different people*?

`pass^k` (all k runs succeed) means something different for each. You'll choose one in Part B.
""")

md("""
## 7. What this environment can't tell you
### 7.1 Is the student realistic?
We compared the rules with one real study, [Bastani et al. (PNAS 2025)](https://www.pnas.org/doi/10.1073/pnas.2422633122): about 1,000 high-school math students practised with plain ChatGPT, with a hint-only AI tutor, or with no AI, then took an exam without AI.

| | Practice, with AI | Exam without AI |
|---|---|---|
| Paper: plain ChatGPT | +48% | **−17%** |
| Paper: hint-only tutor | +127% | about the same as no AI |
| Our student: tutor always gives the answer | +53% | **−29%** (stronger harm than the paper) |
| Our student: tutor gives hints only | +88% | −8% |

The direction matches; the size of the harm doesn't, and the setups differ (in the paper students *chose* to ask for answers and were tested soon after; our tutor hands answers out every time and our test is 2 days later, after forgetting). Separately, our student keeps about half of a mastered idea after a week: that is a design choice, not a measured result.

### 7.2 Known limits (report them, don't hide them)
- **The write-up is never written.** The student asks for help with their write-up, but the simulated student never writes and can't paste text. Tutors that try to help with the document ("paste your paragraph and I'll fix it") get nowhere. Only understanding is measured; the write-up is the student's story, not the task. That gap between what the student asks for and what is measured is itself an evaluation lesson.
- **Replies are short and fixed.** The student answers from a small set of lines ("hm ok", "sure", "can you just tell me the answer"). A tutor can't hold a real conversation with it.
- **No reasoning in the traces.** The tutor model returns only tool calls, so Langfuse shows *what* it did, not *why*.
- **The answer-giving harm is stronger than in the study** (−29% vs −17%, above). Our check used points instead of percent, so it passed; we kept the rules and report it here.
- **The tutor spends a lot of its calls looking around** (reading files, the calendar, its own copy of the readings) before it teaches.
""")

md("""
# Part B · Your turn (20 points)

You design a tutor, run it on a simulated student, read what happened, then change the student and try again. Write your answers in the markdown cells.

## Problem 1: Check your observability setup (2 points)
Run one tutor and confirm its Langfuse trace exists and links to its student record. (No keys? Use a recorded run and its stored link.)
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
## Problem 2: Design a tutor and watch it (6 points)
Write your tutor's strategy. You can change its **instructions**, its **tools** (a smaller set is a real design choice: try removing `quiz_run`, its only sensor), its **model**, and the **observability level** (0 sees the whole computer; 1 sees the student's screen plus what it opens).

Scroll up to the desktop while it runs.
""")
code(CHANGE + '''MY_TUTOR = dict(
    name="my-tutor-v1",
    instructions="Find out what the student already knows with a short quiz before teaching. "
                 "Never give answers; give one hint at a time and assign the matching reading. "
                 "Don't send more than one message in a row without waiting for a reply.",
    model="gpt-5.4-mini",
    tools=None,          # e.g. [t.name for t in make_tools(env) if t.name != "quiz_run"]
    level=None,          # None = the task's default (1); try 0
)
''' + END)
code("""
if have_model():
    mine = run_tutor(env, MY_TUTOR["instructions"], name=MY_TUTOR["name"], model=MY_TUTOR["model"],
                     tools=MY_TUTOR["tools"], level=MY_TUTOR["level"], seed=1000)
else:
    mine = next(r for r in runs if r.get("style") == "socratic")
    replay(env, mine, delay=1.0, verbose=False)
transcript(env, mine)
""")
code("""
compare_runs([mine] + same_student)
""")
md("""
**Answer (Problem 2):**
- In two or three sentences, what did your tutor actually do? Did it follow its instructions?
- Find one moment where it did something you didn't intend. Open its Langfuse trace (link below) and read the model call just before it.
""")
code("""
print("Langfuse:", langfuse_link(mine))
""")

md("""
## Problem 3: Read the evidence and diagnose (4 points)
Pick one thing that went wrong (in your run or any recorded run). Use **both** records.

**Diagnosis:**
- **Run / episode_id:**
- **What went wrong (behaviour):**
- **Category:** reasoning · tool output · prompt/instructions · infrastructure · **observation** (the tutor's view of the student was wrong or incomplete)
- **Langfuse evidence:** span, step, or text
- **Student-record evidence:** step, tracker, hidden-state change
- **What could the tutor have noticed, and from which clue?**
""")

md("""
## Problem 4: Change one thing, across many students (4 points)
Change **one** thing in your tutor and run both versions on the **same 5 students** (different kinds). Report what changed. There is no right answer: say what you see, shortcomings included.
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
                                   level=0, seed=s, instance="friday-build-01-mixed", quiet=True))
    print(len(mixed), "runs")
    display(compare_runs(mixed).sort_values(["student", "tutor"]))
else:
    print("No API key: this problem needs live runs.")
""")
code("""
compare_runs(mixed).groupby("tutor")[["messages", "quizzes", "quiz score in session", "test 2 days later", "minutes used"]].mean().round(2) if mixed else None
""")
md("""
**Answer (Problem 4):** what did your one change do? Did it help some kinds of student and not others? What did it cost (steps, minutes, tokens in Langfuse)?
""")

md("""
## Problem 5: Change the student (4 points)
The simulated student only covers learning, forgetting, attention, reliance on help, and mood. Add a rule for something it's missing. A rule is a small function that runs inside the simulator after every event and nudges numbers. It must stay numeric and use only `rng` for chance, so runs stay repeatable. The tutor never sees your new trait; the grader does.

The example adds **skepticism**: students low on it believe wrong feed posts, and quizzes they pass make them a little more skeptical.
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
**Answer (Problem 5):** what does your rule model, and why? Did any of the 8 checks fail with it on (if so, what does that tell you)? Did your tutor notice the change, and from what clue could it have?
""")

md("""
## Optional: what did "worked" mean to you?
Write down, as code, what you would count as a tutor doing its job, then check it across every run in this notebook. Does it agree with the test 2 days later? Tag each signal you use as **direct** (`post_test`, `true_state`) or **proxy** (quiz scores, tracked minutes, an LLM judge's opinion).
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
Environments are built, not found. Add a tool, give it to your tutor, and see whether it changes what the tutor does. This one is agent-only (it costs the student nothing): it lists the unfinished parts of the student's notes.
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
## Deliverables
- Answers to Problems 2–5 in the cells above, and the notebook with outputs.
- Discussion (6–8 sentences): what did your tutor do well and badly, for which kinds of student, and how do you know? Which of your evidence was **direct** and which was a **proxy**? What would you still not know if this were a real student (no grader, no hidden numbers)?
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
      "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
for i, c in enumerate(cells):
    c["id"] = f"w{i:02d}"
(Path(__file__).resolve().parents[1] / "notebooks" / "learnos_workshop.ipynb").write_text(json.dumps(nb, indent=1))
print(len(cells), "cells")
