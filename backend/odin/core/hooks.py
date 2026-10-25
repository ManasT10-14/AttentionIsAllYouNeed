"""Extension points for the future security suite (guards) and eval suite (DeepEval/LangSmith).

Nothing is implemented here on purpose — the registry is empty and every call is a no-op.
To plug in later:

    from odin.core.hooks import HOOKS
    HOOKS.guards.append(MyPromptInjectionGuard())
    HOOKS.evals.append(MyDeepEvalRecorder())

or list import paths in env ODIN_GUARD_HOOKS / ODIN_EVAL_HOOKS ("pkg.mod:Class,pkg.mod:Other").

A guard returns the (possibly rewritten) payload, or raises `Blocked` to stop the call.
"""
from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class Blocked(Exception):
    """Raised by a guard to veto an LLM call, tool call, ingest or email."""


@runtime_checkable
class GuardHook(Protocol):
    def pre_llm(self, agent: str, messages: list) -> list: ...
    def post_llm(self, agent: str, output: Any) -> Any: ...
    def pre_tool(self, agent: str, tool: str, scope: str, args: dict) -> dict: ...
    def post_tool(self, agent: str, tool: str, result: Any) -> Any: ...
    def on_ingest(self, doc_text: str, meta: dict) -> str: ...
    def on_email(self, raw: str, meta: dict) -> str: ...


@runtime_checkable
class EvalHook(Protocol):
    def record(self, kind: str, agent: str, inputs: Any, output: Any, meta: dict) -> None: ...


@dataclass
class HookRegistry:
    guards: list = field(default_factory=list)
    evals: list = field(default_factory=list)

    def _chain(self, method: str, value, *args):
        for g in self.guards:
            fn = getattr(g, method, None)
            if fn:
                value = _call(fn, method, args, value)
        return value

    def pre_llm(self, agent, messages):
        return self._chain("pre_llm", messages, agent)

    def post_llm(self, agent, output):
        return self._chain("post_llm", output, agent)

    def pre_tool(self, agent, tool, scope, args):
        return self._chain("pre_tool", args, agent, tool, scope)

    def post_tool(self, agent, tool, result):
        return self._chain("post_tool", result, agent, tool)

    def on_ingest(self, doc_text, meta):
        return self._chain("on_ingest", doc_text, meta)

    def on_email(self, raw, meta):
        return self._chain("on_email", raw, meta)

    def record(self, kind, agent, inputs, output, meta):
        for e in self.evals:
            try:
                e.record(kind, agent, inputs, output, meta)
            except Exception:   # eval must never break the product path
                pass


def _call(fn, method, args, value):
    # positional order matches the Protocol signatures above
    if method in ("on_ingest", "on_email"):
        return fn(value, *args)
    return fn(*args, value)


def _load(env: str) -> list:
    out = []
    for path in filter(None, (os.getenv(env, "") or "").split(",")):
        mod, cls = path.strip().split(":")
        out.append(getattr(importlib.import_module(mod), cls)())
    return out


HOOKS = HookRegistry(guards=_load("ODIN_GUARD_HOOKS"), evals=_load("ODIN_EVAL_HOOKS"))
