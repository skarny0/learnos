"""JSONL trace writer. One file per episode. Hidden state is logged (for the grader/replay) but
never returned through the API."""
from __future__ import annotations
import json
import time
import uuid
from pathlib import Path


class TraceWriter:
    def __init__(self, root: Path, instance_id: str, seed: int):
        root.mkdir(parents=True, exist_ok=True)
        # episode_id names the file and is returned by /reset, so client-side traces (Langfuse) can link here
        self.episode_id = f"{instance_id}__{seed}__{int(time.time())}_{uuid.uuid4().hex[:6]}"
        self.path = root / f"{self.episode_id}.jsonl"
        self.f = self.path.open("a")

    def _w(self, rec: dict):
        self.f.write(json.dumps({"ts": time.time(), **rec}, default=str) + "\n")
        self.f.flush()

    def episode_start(self, instance, hidden):
        self._w({"type": "episode_start", "episode_id": self.episode_id, "instance": instance.model_dump(),
                 "hidden": hidden.model_dump() if hidden else None})

    def step(self, **kw):
        h = kw.pop("hidden", None)
        self._w({"type": "step", **kw, "hidden": h.model_dump() if h else None})

    def event(self, ev: dict):
        self._w({"type": "world_event", **ev})

    def episode_end(self, termination, hidden):
        self._w({"type": "episode_end", "termination": termination,
                 "hidden": hidden.model_dump() if hidden else None})
        self.close()

    def close(self):
        if not self.f.closed:
            self.f.close()
