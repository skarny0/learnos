"""Build smolagents Tool classes from the env's /tools registry. One Tool per action.
The tool list IS the action space; students can subset it to study tool-set-size effects."""
from __future__ import annotations
import inspect
from smolagents import Tool
from .client import LearnOS

_TYPE = {"string": "string", "integer": "integer", "number": "number"}


def make_tools(client: LearnOS, include: list[str] | None = None) -> list[Tool]:
    tools = []
    for spec in client.tools():
        if include and spec["name"] not in include:
            continue
        tools.append(_make_tool(client, spec))
    return tools


def _status(out: dict) -> str:
    """One line after every tool result: the clock, the budget, unread messages. This is the observation
    the agent would otherwise never see (smolagents only passes tool outputs to the model)."""
    if out.get("done"):
        return "\n[episode done]"
    o, b = out.get("observation") or {}, (out.get("observation") or {}).get("budget") or {}
    if not b:
        return ""
    unread, scr = o.get("unread_messages"), o.get("screen")
    return (f"\n[status] session time {o.get('t', 0)}/{b.get('learner_minutes')} min used · step {o.get('step')}/{b.get('agent_steps')}"
            + (f" · {unread} unread message(s)" if unread else "")
            + (f"\n[student's screen] {scr['app']}: {scr['shows']}" if scr else ""))


def _make_tool(client: LearnOS, spec: dict) -> Tool:
    inputs = {k: {"type": _TYPE.get(v["type"], "string"), "description": v.get("description", "")}
              for k, v in spec["inputs"].items()}

    # smolagents validates that forward()'s parameters match `inputs`, and CodeAgent may call
    # tools positionally, so give forward a real signature built from the spec.
    params = [inspect.Parameter(k, inspect.Parameter.POSITIONAL_OR_KEYWORD) for k in inputs]
    sig = inspect.Signature(params)

    def forward(self, *args, **kwargs) -> str:
        args_dict = sig.bind(*args, **kwargs).arguments
        out = client.step(self.name, dict(args_dict))
        return out["output"] + _status(out)

    forward.__signature__ = inspect.Signature(
        [inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD), *params])

    _T = type(spec["name"], (Tool,), {                  # class name = span name in Langfuse
        "name": spec["name"], "description": spec["description"],
        "inputs": inputs, "output_type": "string", "forward": forward,
    })
    return _T()
