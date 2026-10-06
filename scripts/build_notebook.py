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
Choosing the environment is half the work. If you want to study whether an agent helps someone **learn**, you need a place where learning can actually go wrong. We'll meet LearnOS one piece at a time, and only at the end write it down formally.

### 1.1 A student's computer, and a task
Seven learning apps (Files, Reader, Notes, Calendar, Messages, Quiz, Browser) plus a social Feed: the desktop above. A tracker records which app is in front of the student, but it can't see their phone.

**The task.** The student is preparing for the **Friday build**, due Friday 10am (about 44 hours after the session starts). The instructor's post in #course says: *"define your environment (state/obs/actions) AND report pass^k on at least 3 seeds."* Their draft write-up has a half-done environment section and an empty Evaluation section, and their first message is *"I started the writeup but I'm stuck on the eval part."* To do it they need three ideas from the week 3 readings: **partial observability**, **attention as a hidden variable**, and **pass@k vs pass^k**. Distractions: a social feed (one peer wrongly posts that pass^k on *one* seed is enough).

**The tutor** gets a 90-minute session with the student and 40 tool calls. It works through **tools** (text in, text out), not the screen; the desktop is a **replay** for us humans. (Extension: give the tutor screenshots and let it click, as computer-use agents do.)
""")
code("""
from learnos_client import make_tools
print(len(make_tools(env)), "tools the tutor can call:\\n", ", ".join(t.name for t in make_tools(env)))
""")

md("""
### 1.2 Be the tutor
Make four tool calls by hand. Each one changes the computer, may cost the student time, and returns text. Scroll up to the desktop while it runs.
""")
code("""
from learnos_client import load_instance
task = load_instance("friday-build-01-demo")
obs = env.reset(task)
print("Student's screen:", obs["screen"], "\\n")
R = "/course/readings/week3/"
for action, args in [
    ("messages_read_channel", {"channel": "dm:student"}),
    ("reader_open_section",   {"path": R + "evaluation.md", "section": "pass@k vs pass^k", "concept": "pass_k"}),
    ("messages_send_to_student", {"text": "If you need it to work on every seed, how many of the k runs have to pass?",
                                  "intent": "hint", "concept": "pass_k"}),
    ("quiz_run",              {"concept": "pass_k", "n_items": 3, "difficulty": 0.5}),
]:
    out = env.step(action, args)
    scr = out["observation"]["screen"]
    print(f"▶ {action}\\n  {out['output']}\\n  [student's screen] {scr['app']}: {scr['shows']}\\n")
""")
md("""
That text is **all a tutor model gets**: what each tool returns, a status line (time used, steps used, unread messages), and one line with the student's screen, as if it were following the student. How much more it sees is the **level** you pick:

| Level | The tutor sees |
|---|---|
| **0** | Everything on the computer (files, notes, calendar, messages, feed), plus the student's screen |
| **1** (default) | Only the student's screen, plus whatever it opens with its tools |
| **2** | Like 1, but the world changes mid-session (a message arrives, the deadline moves) |

### 1.3 What the tutor can't see: the student
Behind the screen is a simulated student who **learns**, **forgets**, **gets distracted**, **asks for help**, and **quits** if nagged. The tutor never sees their mind. The **grader** does: it holds a token the tutor never gets.
""")
code("""
env.step("session_end", {"summary": "driven by hand"})
g = env.grader
ts = g("true_state")
print("hidden student:", {k: round(ts[k], 2) for k in ("attention", "motivation", "reliance")}, "| type:", ts["persona"].get("type"))
print("knows each idea:", {c: round(v, 2) for c, v in ts["p_know"].items()})
print("what a real deployment could measure instead (proxies):",
      {k: v for k, v in g("proxies").items() if k in ("quiz_mean", "n_messages_to_student", "tracked_minutes_by_app")})
""")
md("""
**Every seed is a different student**: focused, distractible, answer-seeking, strong but bored, or slow and steady, with traits drawn from that type's ranges. The tutor isn't told which.

### 1.4 How the student changes: the rules
The student runs on fixed rules (numbers, not an AI), so every run can be repeated and graded fairly. Reading teaches if they're paying attention; a hint teaches less but keeps them working; an answer barely teaches and builds reliance; too many messages annoy them; the feed pulls them away; memory fades. Chance decides the details, from the seed. The tutor isn't told any of this.

We compared the rules with one real study, [Bastani et al. (PNAS 2025)](https://www.pnas.org/doi/10.1073/pnas.2422633122): about 1,000 high-school math students practised with plain ChatGPT, with a hint-only AI tutor, or with no AI, then took an exam without AI.

| | Practice, with AI | Exam without AI |
|---|---|---|
| Paper: plain ChatGPT | +48% | **−17%** |
| Paper: hint-only tutor | +127% | about the same as no AI |
| Our student: tutor always gives the answer | +53% | **−29%** (stronger harm than the paper) |
| Our student: tutor gives hints only | +88% | −8% |

The direction matches; the size of the harm doesn't, and the setups differ (in the paper students *chose* to ask for answers and were tested soon after; our tutor hands answers out every time and our test is 2 days later, after forgetting). Separately, our student keeps about half of a mastered idea after a week: that is a design choice, not a measured result.


### 1.5 No reward
Nothing in LearnOS says whether the tutor did well. The grader returns **facts** (a fixed test now and 2 days later, the hidden state, proxies, flags like "gave answers"), never a score. Deciding what counts as success is your job.
""")
code("""
print("test now / 2 days later:", round(g("post_test")["post_test"], 2), "/", round(g("post_test", delay_hours=48)["post_test"], 2))
print("flags:", g("harms"))
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
### 1.7 Known limits (report them, don't hide them)
- **The write-up is never written.** The student asks for help with it, but the simulated student never writes and can't paste text. Only what they *learn* is measured. Real tutors keep asking "paste your paragraph and I'll fix it" and get nowhere. What the student asks for and what we measure differ: that gap is itself an evaluation lesson.
- **Replies are short and fixed.** The student answers from a small set of lines ("hm ok", "sure", "can you just tell me the answer"). A tutor can't hold a real conversation with it.
- **No reasoning in the traces.** The tutor model returns only tool calls, so Langfuse shows *what* it did, not *why*.
- **The answer-giving harm is stronger than in the study** (−29% vs −17%, see 1.4). Our check used points instead of percent, so it passed; we kept the rules and report it here.
- **The tutor spends a lot of its calls looking around** (reading files, the calendar, its own copy of the readings) before it teaches.
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
