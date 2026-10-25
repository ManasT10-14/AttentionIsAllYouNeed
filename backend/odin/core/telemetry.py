"""Private, best-effort LangSmith spans at shared Odin boundaries.

No prompts, contract text, tool args or answers are submitted as span I/O.
Children using this scoped client inherit the same input/output hiding policy.
"""

import os
from contextlib import contextmanager
from functools import lru_cache, wraps

from langsmith import Client


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
                  hide_inputs=True, hide_outputs=True, timeout_ms=2000,
                  retry_config=Retry(total=0, respect_retry_after_header=False))


def traced(name, run_type="chain"):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            with span(name, run_type):
                return fn(*args, **kwargs)
        return wrapped
    return decorate


@contextmanager
def span(name, run_type="chain", *, run_id=None):
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
        run = stack.enter_context(trace(name, run_type=run_type, inputs={}, run_id=run_id))
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
