"""Evaluation suite: live per-run scoring (live.py) and the on-demand golden suite (suite.py)."""
from __future__ import annotations

import functools
import time


def install():
    """Register the live scorer once when `evals.enabled` (default true) in odin.yaml."""
    from odin.core.config import odin_config
    from odin.core.hooks import HOOKS
    cfg = odin_config().get("evals") or {}
    if not cfg.get("enabled", True):
        return None
    try:   # the scorer reuses the ragnarok harness (eval/); a backend-only image runs without live evals
        from odin.evals.live import LiveScorer
    except ImportError as e:
        import logging
        logging.getLogger("odin.evals").warning("live evals disabled: %s", e)
        return None
    existing = next((e for e in HOOKS.evals if isinstance(e, LiveScorer)), None)
    if existing:
        return existing
    scorer = LiveScorer(cfg)
    HOOKS.evals.append(scorer)
    return scorer


def scored(kind: str):
    """Give a synchronous call (Ask) its own run id so it is captured and scored like a graph run.
    Inside an existing run (e.g. the ragnarok worker) it is a pass-through."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(company_id, question, *a, **kw):
            from odin.core import budget as budget_mod
            from odin.core.context import maybe_current, run_ctx
            from odin.core.hooks import HOOKS
            from odin.core.models import new_id
            c = maybe_current()
            if c and c.run_id:
                return fn(company_id, question, *a, **kw)
            run_id, t0 = new_id(kind), time.perf_counter()
            with run_ctx(company_id, run_id=run_id):
                try:
                    out = fn(company_id, question, *a, **kw)
                finally:
                    b = budget_mod.release(run_id)
            HOOKS.record("run", kind, question, out, {"run_id": run_id, "company_id": company_id, "budget": b,
                                                      "question": question,
                                                      "latency_ms": (time.perf_counter() - t0) * 1000})
            return out
        return wrapper
    return deco
