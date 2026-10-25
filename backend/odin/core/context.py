"""Per-run context (company / run / scenario / agent) carried in a contextvar so tools and the
store don't need it threaded through every call. Set by `agent_node` at node entry."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class RunCtx:
    company_id: str
    run_id: Optional[str] = None
    scenario_id: Optional[str] = None
    agent: str = "system"
    user_role: str = "system"


_ctx: ContextVar[Optional[RunCtx]] = ContextVar("odin_run_ctx", default=None)


def current() -> RunCtx:
    c = _ctx.get()
    if c is None:
        raise RuntimeError("No RunCtx set — wrap the call in run_ctx(...)")
    return c


def maybe_current() -> Optional[RunCtx]:
    return _ctx.get()


@contextmanager
def run_ctx(company_id: str | None = None, **kw):
    base = _ctx.get()
    if base is None:
        new = RunCtx(company_id=company_id or "", **kw)
    else:
        new = replace(base, **({"company_id": company_id} if company_id else {}), **kw)
    tok = _ctx.set(new)
    try:
        yield new
    finally:
        _ctx.reset(tok)
