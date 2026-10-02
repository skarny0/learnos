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


def _find_instances() -> Path:
    if os.getenv("LEARNOS_INSTANCES_DIR"):
        return Path(os.environ["LEARNOS_INSTANCES_DIR"])
    import learnos_env                                   # package __init__ only; no env vars read yet
    for cand in (Path(learnos_env.__file__).resolve().parents[2] / "instances",   # cloned repo layout
                 Path.cwd() / "learnos" / "instances", Path.cwd() / "instances"):
        if (cand / "materials").exists():
            return cand
    raise FileNotFoundError("Could not find the LearnOS instances folder; pass instances_dir=...")


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
    if port in _servers or _up(base):                    # re-running the cell is harmless
        return LearnOS(base, grader_token=os.environ.get("LEARNOS_GRADER_TOKEN", token))

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
    print(f"LearnOS running ({mode} mode). Data in {os.environ['LEARNOS_DATA_DIR']}. Call show() to see the desktop.")
    return LearnOS(base, grader_token=token)


def _path(open: list[str] | None) -> str:
    return "/" + (f"?open={','.join(open)}" if open else "")


def show(port: int = 8000, height: int = 720, open: list[str] | None = None) -> None:
    """Embed the LearnOS desktop in the notebook output. open=["calendar", "feed"] pre-opens windows."""
    try:
        from google.colab import output                 # Colab: proxy the kernel's port into an iframe
        output.serve_kernel_port_as_iframe(port, path=_path(open), height=str(height))
    except ImportError:
        from IPython.display import IFrame, display
        display(IFrame(f"http://localhost:{port}{_path(open)}", width="100%", height=height))


def show_in_tab(port: int = 8000, open: list[str] | None = None) -> None:
    """Open the desktop in its own browser tab (more room than an output cell)."""
    try:
        from google.colab import output
        output.serve_kernel_port_as_window(port, path=_path(open), anchor_text="Open the LearnOS desktop")
    except ImportError:
        from IPython.display import HTML, display
        display(HTML(f'<a href="http://localhost:{port}{_path(open)}" target="_blank">Open the LearnOS desktop</a>'))
