"""Thin HTTP client. The agent never gets the grader token; the eval runner does."""
from __future__ import annotations
import requests


class LearnOS:
    def __init__(self, base: str = "http://localhost:8000", grader_token: str | None = None):
        self.base = base.rstrip("/")
        self.token = grader_token

    def health(self):
        return requests.get(f"{self.base}/health").json()

    def tools(self):
        return requests.get(f"{self.base}/tools").json()

    def reset(self, instance: dict):
        return requests.post(f"{self.base}/reset", json=instance).json()

    def step(self, action: str, args: dict | None = None):
        return requests.post(f"{self.base}/step", json={"action": action, "args": args or {}}).json()

    def observe(self):
        return requests.get(f"{self.base}/observe").json()

    # grader ---------------------------------------------------------------
    def grader(self, signal: str, **params):
        h = {"X-Grader-Token": self.token} if self.token else {}
        r = requests.get(f"{self.base}/grader/{signal}", params=params, headers=h)
        if r.status_code == 403:
            raise PermissionError(r.json()["detail"])
        r.raise_for_status()
        return r.json()
