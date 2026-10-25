"""Best-effort LangSmith spans at shared Odin boundaries.

Span and child chat-model I/O is submitted (so traces are debuggable) after secret redaction:
API keys / bearer tokens / passwords are replaced before anything leaves the process.
Error strings stay hidden (provider errors can echo request bodies).
"""

import os
import inspect
import re
from contextlib import contextmanager
from functools import lru_cache, wraps

from langsmith import Client

_SECRET = re.compile(
    r"(sk-[A-Za-z0-9_\-]{12,}|gsk_[A-Za-z0-9]{12,}|lsv2_[A-Za-z0-9_]{12,}|AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}"
    r"|AIza[0-9A-Za-z_\-]{20,}|xox[abp]-[A-Za-z0-9\-]{10,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]*"
    r"|(?i:bearer)\s+[A-Za-z0-9._~+/\-]{16,}"
    r"|(?i:(?:api[_-]?key|secret|token|password|passwd)[\"']?\s*[:=]\s*)[\"']?[^\s\"',}]{6,})")


def redact(x):
    """Recursively mask obvious secrets in strings of a JSON-like structure."""
    if isinstance(x, str):
        return _SECRET.sub("[REDACTED]", x)
    if isinstance(x, dict):
        return {k: redact(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [redact(v) for v in x]
    return x


def _plain(x, depth=0):
    """Make span I/O JSON-friendly: pydantic → dict, messages → role/content, long text capped."""
    if hasattr(x, "model_dump"):
        try:
            return _plain(x.model_dump(mode="json"), depth)
        except Exception:
            return str(x)[:2000]
    if isinstance(x, dict):
        return {str(k): _plain(v, depth + 1) for k, v in x.items()} if depth < 6 else str(x)[:500]
    if isinstance(x, (list, tuple, set)):
        return [_plain(v, depth + 1) for v in list(x)[:60]]
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x[:20000] if isinstance(x, str) else x
    return str(x)[:500]


class PrivateClient(Client):
    """Apply the privacy policy to auto-generated children as well as our spans."""

    @staticmethod
    def _private(kwargs):
        if kwargs.get("error"):
            kwargs["error"] = "Product execution failed"
        return kwargs

    def create_run(self, *args, **kwargs):
        return super().create_run(*args, **self._private(kwargs))

    def update_run(self, *args, **kwargs):
        return super().update_run(*args, **self._private(kwargs))


def enabled():
    return os.getenv("LANGSMITH_TRACING", "").lower() == "true" and bool(os.getenv("LANGSMITH_API_KEY"))


@lru_cache
def client():
    from urllib3.util import Retry
    return PrivateClient(api_key=os.environ["LANGSMITH_API_KEY"],
                  api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
                  hide_inputs=redact, hide_outputs=redact, timeout_ms=2000,
                  retry_config=Retry(total=0, respect_retry_after_header=False))


def traced(name, run_type="chain"):
    """Span with the call's arguments as inputs and its return value as outputs."""
    def decorate(fn):
        sig = inspect.signature(fn)

        @wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                inputs = _plain(dict(sig.bind(*args, **kwargs).arguments))
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
            run.add_outputs(_plain(out) if isinstance(_plain(out), dict) else {"output": _plain(out)})
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
        run = stack.enter_context(trace(name, run_type=run_type, inputs=inputs or {}, run_id=run_id,
                                        metadata=meta, tags=list(tags or []) or None))
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
