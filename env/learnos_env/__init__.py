"""LearnOS environment: a reward-free, seedable learning workspace.

Module map
----------
state.py     Pydantic models for the whole workspace (visible) + learner (hidden).
apps/        One module per app. Each exposes actions as pure functions on state.
sim/         Simulated learner: numeric dynamics (code) + optional text renderer (LLM).
env.py       Episode logic: reset(seed, level), step(action), observation builder, events.
grader.py    Privileged read interface over hidden state. Signals only, never a reward.
trace.py     JSONL trace writer (one file per episode).
server.py    FastAPI surface: /reset /step /observe /grader/* /ws (UI feed).
"""
__version__ = "0.0.1"
