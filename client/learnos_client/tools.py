"""Build smolagents Tool classes from the env's /tools registry. One Tool per action.
The tool list IS the action space; students can subset it to study tool-set-size effects."""
from __future__ import annotations
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


def _make_tool(client: LearnOS, spec: dict) -> Tool:
    inputs = {k: {"type": _TYPE.get(v["type"], "string"), "description": v.get("description", "")}
              for k, v in spec["inputs"].items()}

    class _T(Tool):
        name = spec["name"]
        description = spec["description"]
        output_type = "string"

        def __init__(self):
            super().__init__()
            self.inputs = inputs

        def forward(self, **kwargs) -> str:
            out = client.step(self.name, kwargs)
            return out["output"] + ("\n[episode done]" if out.get("done") else "")

    _T.__name__ = f"Tool_{spec['name']}"
    return _T()
