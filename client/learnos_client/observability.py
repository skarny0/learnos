"""Langfuse setup for LearnOS runs. One call before building agents:

    from learnos_client import setup_langfuse
    lf = setup_langfuse()        # reads LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL

Langfuse's default export filter keeps only spans it recognises as LLM instrumentation, which would
drop the `learnos.episode` span run_episode wraps each run in (the one carrying episode_id, seed and
config). This keeps it, then instruments smolagents so every model call and tool call is a span.
"""
from __future__ import annotations
import os


def setup_langfuse(instrument: bool = True):
    os.environ.setdefault("OTEL_ATTRIBUTE_COUNT_LIMIT", "1024")     # smolagents spans carry many attributes
    from langfuse import Langfuse
    from langfuse.span_filter import is_default_export_span
    lf = Langfuse(should_export_span=lambda s: is_default_export_span(s)
                  or (s.instrumentation_scope is not None and s.instrumentation_scope.name == "learnos"))
    if not lf.auth_check():
        raise RuntimeError("Langfuse authentication failed: check LANGFUSE_* keys and LANGFUSE_BASE_URL")
    if instrument:
        from openinference.instrumentation.smolagents import SmolagentsInstrumentor
        SmolagentsInstrumentor().instrument()
    return lf
