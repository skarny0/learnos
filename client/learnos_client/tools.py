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
        return out["output"] + ("\n[episode done]" if out.get("done") else "")

    forward.__signature__ = inspect.Signature(
        [inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD), *params])

    _T = type(spec["name"], (Tool,), {                  # class name = span name in Langfuse
        "name": spec["name"], "description": spec["description"],
        "inputs": inputs, "output_type": "string", "forward": forward,
    })
    return _T()
