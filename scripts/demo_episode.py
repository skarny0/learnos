"""Play a short scripted episode slowly so you can watch it on the desktop (http://localhost:8080).

    python scripts/demo_episode.py              # 1.5 s between steps
    python scripts/demo_episode.py --delay 0.3

Stdlib only. This is a demo, not one of the cached policies (see PLAN.md 1.4).
"""
import argparse, json, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = "http://localhost:8000"
R = "/course/readings/week3/"

STEPS = [
    ("messages_read_channel", {"channel": "#course"}),
    ("messages_read_channel", {"channel": "dm:student"}),
    ("notes_read", {"note_id": "writeup"}),
    ("calendar_list", {}),
    ("feed_scroll", {"n": 10}),
    ("files_ls", {"path": R.rstrip("/")}),
    ("files_outline", {"path": R + "environments.md"}),
    ("reader_open_section", {"path": R + "environments.md", "section": "Partial observability (POMDP)", "concept": "pomdp"}),
    ("quiz_run", {"concept": "pomdp", "n_items": 3, "difficulty": 0.5}),
    ("messages_send_to_student", {"text": "Why does a POMDP agent need a belief instead of the state?", "intent": "hint", "concept": "pomdp"}),
    ("session_wait", {"minutes": 20}),
    ("feed_mute", {"source": "#memes"}),
    ("files_outline", {"path": R + "evaluation.md"}),
    ("calendar_add_block", {"title": "Review pass^k", "start": 200, "duration": 45, "concept": "pass_k"}),
    ("notes_append", {"note_id": "writeup", "text": "## Evaluation (scaffold)\n- report pass^k over >= 3 seeds\n- one failure case"}),
    ("session_end", {"summary": "Checked requirements, assigned POMDP reading, quizzed, scheduled pass^k review, scaffolded eval."}),
]


def post(path, body):
    req = urllib.request.Request(ENV + path, json.dumps(body).encode(), {"content-type": "application/json"})
    return json.load(urllib.request.urlopen(req))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default="friday-build-01")
    ap.add_argument("--delay", type=float, default=1.5)
    a = ap.parse_args()
    post("/reset", json.loads((ROOT / "instances" / f"{a.instance}.json").read_text()))
    for action, args in STEPS:
        time.sleep(a.delay)
        out = post("/step", {"action": action, "args": args})
        print(f"#{out['step']:>2} {action:<26} {out['output'].splitlines()[0][:70]}")
        if out["done"]:
            break
