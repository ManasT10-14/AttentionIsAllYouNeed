"""Best-effort LangSmith spans at shared Odin boundaries.

Remote I/O defaults to metadata-only; ODIN_TRACE_CONTENT=redacted explicitly enables
content with the shared recursive privacy policy applied before enqueue.
Error strings stay hidden (provider errors can echo request bodies).

Metadata-only allows bounded scalar identifiers in METADATA_IDENTIFIERS, fixed
agent/provider/run-kind values, and the typed LangGraph fields below. SDK extra
fields other than this metadata are omitted. Tags allow fixed agents/providers,
``whatif``, and ``contract:<identifier>``. Arbitrary prose/nested metadata is omitted.
Redacted-content opt-in keeps recursively redacted metadata/tags. Binary attachments
are always omitted, including in opt-in mode.
"""

import inspect
import os
import re
from contextlib import contextmanager
from functools import lru_cache, wraps

from langsmith import Client
from odin.core.privacy import redact, redact_text

METADATA_IDENTIFIERS = frozenset({
    "company_id", "run_id", "scenario_id", "contract_id", "invocation_id", "trace_id",
    "prompt_hash", "config_revision", "source_id", "source_hash", "document_hash",
    "dataset_id", "dataset_version", "evaluator_version", "detector_version", "checkpoint_id",
    "langgraph_checkpoint_ns", "ls_model_name", "ls_model_type",
})
TRACE_AGENTS = frozenset({"odin", "thor", "norns", "loki", "heimdall", "tyr", "synth",
                          "email_parse", "ask", "security", "system"})
TRACE_PROVIDERS = frozenset({"bedrock", "openai", "anthropic", "groq", "fake"})
TRACE_RUN_KINDS = TRACE_AGENTS | {"analysis", "update", "event", "workstream", "whatif", "scenario"}
LANGGRAPH_NODES = TRACE_AGENTS | {
    "plan", "pipeline", "cross", "final", "thor_extract", "loki_attack", "loki_cross", "thor_clarify",
    "loki_revisit", "heimdall_verify", "loki_rebut", "tyr_rule", "tyr_actions", "odin_check", "map",
    "recompute", "reassess", "verify", "rebut", "rule", "decide", "diff", "patch", "invalidate",
    "rerun", "amend", "report", "__start__", "__end__",
}
_METADATA_ENUMS = {"agent": TRACE_AGENTS, "provider": TRACE_PROVIDERS, "ls_provider": TRACE_PROVIDERS,
                   "run_kind": TRACE_RUN_KINDS, "langgraph_node": LANGGRAPH_NODES}
_IDENTIFIER = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.:/-]{0,159}\Z")


def _content_optin():
    return os.getenv("ODIN_TRACE_CONTENT", "").lower() == "redacted"


def trace_metadata(value):
    if _content_optin():
        return _plain(redact(value))
    if not isinstance(value, dict):
        return {}
    allowed = {}
    for key, item in value.items():
        if key in METADATA_IDENTIFIERS and isinstance(item, str) and _IDENTIFIER.fullmatch(item):
            allowed[key] = item
        elif key in _METADATA_ENUMS and isinstance(item, str) and item in _METADATA_ENUMS[key]:
            allowed[key] = item
        elif key == "langgraph_step" and type(item) is int and item >= 0:
            allowed[key] = item
        elif key in {"langgraph_triggers", "langgraph_path"} and isinstance(item, (list, tuple)):
            if len(item) <= 8 and all(isinstance(part, str) and _IDENTIFIER.fullmatch(part) for part in item):
                allowed[key] = list(item)
    return redact(allowed)


def trace_tags(value):
    if _content_optin():
        return _plain(redact(value))
    return redact([item for item in value or [] if isinstance(item, str) and
                   (item in TRACE_AGENTS | TRACE_PROVIDERS | {"whatif"} or
                    item.startswith("contract:") and _IDENTIFIER.fullmatch(item[len("contract:"):]))])


def trace_name(value):
    safe = redact_text(value)
    return safe if _content_optin() or _IDENTIFIER.fullmatch(safe) else "odin:span"


def trace_content(value):
    """Remote traces contain no content unless redacted-content mode is explicitly enabled."""
    if _content_optin():
        return _plain(redact(value))
    return {"content_omitted": True}


def _plain(x, depth=0):
    """Make span I/O JSON-friendly: pydantic → dict, messages → role/content, long text capped."""
    if hasattr(x, "model_dump"):
        try:
            return _plain(x.model_dump(mode="json"), depth)
        except Exception:
            return redact_text(str(x))[:2000]
    if isinstance(x, dict):
        return {redact_text(str(k)): _plain(v, depth + 1) for k, v in x.items()} if depth < 6 else redact_text(str(x))[:500]
    if isinstance(x, (list, tuple, set)):
        return [_plain(v, depth + 1) for v in list(x)[:60]]
    if isinstance(x, (str, int, float, bool)) or x is None:
        return redact_text(x)[:20000] if isinstance(x, str) else x
    return redact_text(str(x))[:500]


class PrivateClient(Client):
    """Apply the privacy policy to auto-generated children as well as our spans."""

    @staticmethod
    def _private(kwargs):
        kwargs = dict(kwargs)
        # Binary attachments have no inspectable text boundary and are never uploaded here.
        if "attachments" in kwargs:
            kwargs["attachments"] = {}
        if "extra" in kwargs and kwargs["extra"] is not None:
            extra = kwargs["extra"]
            kwargs["extra"] = _plain(redact(extra)) if _content_optin() else {
                "metadata": trace_metadata(extra.get("metadata", {}) if isinstance(extra, dict) else {})}
        if "metadata" in kwargs:
            kwargs["metadata"] = trace_metadata(kwargs["metadata"])
        if "tags" in kwargs:
            kwargs["tags"] = trace_tags(kwargs["tags"])
        if kwargs.get("name"):
            kwargs["name"] = trace_name(kwargs["name"])
        for key in ("inputs", "outputs", "serialized", "events"):
            if key in kwargs and kwargs[key] is not None:
                if key == "events" and not _content_optin():
                    kwargs[key] = []
                else:
                    kwargs[key] = trace_content(kwargs[key])
        if kwargs.get("error"):
            kwargs["error"] = "Product execution failed"
        return redact(kwargs)

    def create_run(self, name, inputs, run_type, **kwargs):
        return super().create_run(trace_name(name), trace_content(inputs), run_type, **self._private(kwargs))

    def update_run(self, *args, **kwargs):
        return super().update_run(*args, **self._private(kwargs))


def enabled():
    return os.getenv("LANGSMITH_TRACING", "").lower() == "true" and bool(os.getenv("LANGSMITH_API_KEY"))


@lru_cache
def client():
    from urllib3.util import Retry
    return PrivateClient(api_key=os.environ["LANGSMITH_API_KEY"],
                  api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
                  hide_inputs=trace_content, hide_outputs=trace_content, timeout_ms=2000,
                  retry_config=Retry(total=0, respect_retry_after_header=False))


def traced(name, run_type="chain"):
    """Span with the call's arguments as inputs and its return value as outputs."""
    def decorate(fn):
        sig = inspect.signature(fn)

        @wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                inputs = _plain(redact(dict(sig.bind(*args, **kwargs).arguments)))
            except Exception:
                inputs = {}
            flat = {**(inputs.get("meta") or {}), **inputs} if isinstance(inputs.get("meta"), dict) else inputs
            meta = {k: flat[k] for k in ("agent", "contract_id", "company_id") if isinstance(flat.get(k), str)}
            with span(name, run_type, inputs=inputs, metadata=meta, tags=[v for v in (meta.get("agent"),) if v]) as run:
                out = fn(*args, **kwargs)
                _set_outputs(run, out)
                return out
        return wrapped
    return decorate


def _set_outputs(run, out):
    try:
        if run is not None:
            payload = trace_content(out)
            run.add_outputs(payload if isinstance(payload, dict) else {"output": payload})
    except Exception:
        pass


@contextmanager
def span(name, run_type="chain", *, run_id=None, inputs=None, metadata=None, tags=None):
    if not enabled():
        yield None
        return
    # Setup/publishing errors must not interrupt execution. Product errors still propagate.
    from contextlib import ExitStack
    stack = ExitStack()
    try:
        from langsmith import trace, tracing_context
        stack.enter_context(tracing_context(enabled=True, client=client(),
                            project_name=os.getenv("LANGSMITH_PROJECT", "ragnarok-odin")))
        from odin.core.context import maybe_current
        c = maybe_current()
        meta = {**({"company_id": c.company_id, "run_id": c.run_id, "scenario_id": c.scenario_id} if c else {}), **(metadata or {})}
        meta = {k: v for k, v in meta.items() if v is not None}
        run = stack.enter_context(trace(trace_name(name), run_type=run_type, inputs=trace_content(inputs or {}), run_id=run_id,
                                        metadata=trace_metadata(meta), tags=trace_tags(list(tags or [])) or None))
    except Exception:
        stack.close()
        yield None
        return
    try:
        yield run
    except BaseException:
        # Do not send exception strings: provider errors may contain request bodies.
        try:
            run.end(error="Product execution failed")
        except Exception:
            pass
        raise
    finally:
        try:
            stack.close()
        except Exception:
            pass
