"""Run lifecycle + live work plan (FR1.2/1.3, NFR4). Graphs run in worker threads."""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime
from typing import Callable

from odin.core import budget as budget_mod
from odin.core.config import settings
from odin.core.context import run_ctx
from odin.core.models import Workstream
from odin.db import repo
from odin.db.session import db
from odin.db.tables import Run

log = logging.getLogger("odin.runs")
_plans: dict[str, dict[str, Workstream]] = {}
_lock = threading.Lock()


def new_run(company_id: str, kind: str, scenario_id: str | None = None) -> str:
    run_id = str(uuid.uuid4())
    with db() as s:
        s.add(Run(id=run_id, company_id=company_id, kind=kind, status="running", scenario_id=scenario_id))
    return run_id


def set_plan(run_id: str, workstreams: list[Workstream]) -> None:
    with _lock:
        _plans[run_id] = {w.id: w for w in workstreams}
    _persist(run_id)


def update_ws(run_id: str, ws_id: str, **fields) -> None:
    with _lock:
        plan = _plans.get(run_id)
        if not plan or ws_id not in plan:
            return
        plan[ws_id] = plan[ws_id].model_copy(update=fields)
    _persist(run_id)


def plan(run_id: str) -> list[Workstream]:
    with _lock:
        return list(_plans.get(run_id, {}).values())


def _persist(run_id: str) -> None:
    ws = [w.model_dump() for w in plan(run_id)]
    repo.update_run(run_id, workplan={"workstreams": ws}, budget=budget_mod.for_run(run_id).to_dict())


def start(company_id: str, kind: str, fn: Callable[[str], str], *, scenario_id: str | None = None,
          run_id: str | None = None, background: bool = True) -> str:
    """fn(run_id) -> final status ('done' | 'partial' | 'failed'). Runs inside a RunCtx."""
    run_id = run_id or new_run(company_id, kind, scenario_id)

    def _go():
        status, err = "failed", ""
        with run_ctx(company_id, run_id=run_id, scenario_id=scenario_id, agent="odin"):
            try:
                status = fn(run_id) or "done"
            except Exception as e:   # noqa: BLE001
                log.exception("run %s failed", run_id)
                err = f"{type(e).__name__}: {e}"[:1000]
        b = budget_mod.release(run_id)
        repo.update_run(run_id, status=status, error=err, budget=b, finished_at=datetime.utcnow(),
                        trace_url=_trace_url(run_id))
        with _lock:
            _plans.pop(run_id, None)

    if background:
        threading.Thread(target=_go, name=f"run-{kind}-{run_id[:8]}", daemon=True).start()
    else:
        _go()
    return run_id


def _trace_url(run_id: str) -> str:
    """Best-effort LangSmith link for the root run (the graph is invoked with this run id)."""
    import os
    if not os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGSMITH_TRACING", "").lower() != "true":
        return ""
    try:
        from langsmith import Client
        c = Client()
        return c.get_run_url(run=c.read_run(run_id))
    except Exception:   # noqa: BLE001
        return ""


def graph_config(run_id: str, kind: str, **meta) -> dict:
    settings()
    return {"run_id": uuid.UUID(run_id), "run_name": f"odin-{kind}", "tags": ["odin", kind],
            "metadata": {"run_kind": kind, **meta}, "configurable": {"thread_id": run_id},
            "recursion_limit": 200}
