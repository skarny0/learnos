"""Run LearnOS inside a notebook (Colab or local Jupyter) and show its desktop in an output cell.

    from learnos_client import start, show
    env = start()          # LearnOS server in a background thread; returns a client with the grader token
    show()                 # the desktop, embedded below the cell (live while agents run in other cells)

No Docker needed: the env server serves the prebuilt desktop itself (learnos_env/ui_dist).
"""
from __future__ import annotations
import os
import secrets
import threading
import time
from pathlib import Path

import requests

from .client import LearnOS

_servers: dict[int, object] = {}
_current = {"port": 8000}                              # the server start() last connected to; show() follows it


def _find_instances() -> Path:
    if os.getenv("LEARNOS_INSTANCES_DIR"):
        return Path(os.environ["LEARNOS_INSTANCES_DIR"])
    import learnos_env                                   # package __init__ only; no env vars read yet
    for cand in (Path(learnos_env.__file__).resolve().parents[2] / "instances",   # cloned repo layout
                 Path.cwd() / "learnos" / "instances", Path.cwd() / "instances"):
        if (cand / "materials").exists():
            return cand
    raise FileNotFoundError("Could not find the LearnOS instances folder; pass instances_dir=...")


def _token_ok(base: str, token: str) -> bool:
    """403 = the server refuses this grader token; anything else (e.g. 400 'reset first') = it accepts it."""
    try:
        return requests.get(f"{base}/grader/cost", headers={"X-Grader-Token": token}, timeout=1).status_code != 403
    except requests.RequestException:
        return False


def _up(base: str) -> bool:
    try:
        return requests.get(f"{base}/health", timeout=0.5).ok
    except requests.RequestException:
        return False


def start(port: int = 8000, mode: str = "sim", data_dir: str = "learnos_data",
          instances_dir: str | None = None, grader_token: str | None = None) -> LearnOS:
    """Start the LearnOS server in this kernel (once) and return a client for it.

    The client holds the grader token for your reward/success code. Give your agent
    make_tools(env), never the token itself."""
    base = f"http://localhost:{port}"
    token = grader_token or os.environ.get("LEARNOS_GRADER_TOKEN") or secrets.token_hex(8)
    if port in _servers:                                 # re-running the cell is harmless
        _current["port"] = port
        return LearnOS(base, grader_token=os.environ["LEARNOS_GRADER_TOKEN"])
    if _up(base):                                        # someone else's server (e.g. docker compose up, another kernel)
        theirs = grader_token or os.environ.get("LEARNOS_GRADER_TOKEN", "change-me")
        if _token_ok(base, theirs):
            _current["port"] = port
            print(f"Using the LearnOS server already running on port {port}.")
            return LearnOS(base, grader_token=theirs)
        free = next(p for p in range(port + 1, port + 50) if not _up(f"http://localhost:{p}"))
        print(f"Port {port} has a LearnOS server that doesn't accept this grader token "
              f"(probably another notebook). Starting a fresh one on port {free}.")
        return start(free, mode, data_dir, instances_dir, grader_token)

    # The env reads these at import time, so set them before importing the server.
    os.environ["LEARNOS_INSTANCES_DIR"] = str(Path(instances_dir) if instances_dir else _find_instances())
    os.environ["LEARNOS_DATA_DIR"] = str(Path(data_dir).resolve())
    os.environ["LEARNOS_MODE"] = mode
    os.environ["LEARNOS_GRADER_TOKEN"] = token

    import uvicorn
    from learnos_env.server import app
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True, name="learnos-server").start()
    _servers[port] = server
    for _ in range(100):
        if _up(base):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(f"LearnOS did not start on port {port}")
    _current["port"] = port
    print(f"LearnOS running ({mode} mode). Data in {os.environ['LEARNOS_DATA_DIR']}. Call show() to see the desktop.")
    return LearnOS(base, grader_token=token)


def _path(open: list[str] | None) -> str:
    return "/" + (f"?open={','.join(open)}" if open else "")


def show(port: int | None = None, height: int = 720, open: list[str] | None = None) -> None:
    """Embed the LearnOS desktop in the notebook output. open=["calendar", "feed"] pre-opens windows."""
    port = port or _current["port"]
    try:
        from google.colab import output                 # Colab: proxy the kernel's port into an iframe
        output.serve_kernel_port_as_iframe(port, path=_path(open), height=str(height))
    except ImportError:
        from IPython.display import IFrame, display
        display(IFrame(f"http://localhost:{port}{_path(open)}", width="100%", height=height))


def show_in_tab(port: int | None = None, open: list[str] | None = None) -> None:
    """Open the desktop in its own browser tab (more room than an output cell)."""
    port = port or _current["port"]
    try:
        from google.colab import output
        output.serve_kernel_port_as_window(port, path=_path(open), anchor_text="Open the LearnOS desktop")
    except ImportError:
        from IPython.display import HTML, display
        display(HTML(f'<a href="http://localhost:{port}{_path(open)}" target="_blank">Open the LearnOS desktop</a>'))
