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
_links: dict[str, dict] = {}    # run_id -> {event_id|contract_id}, persisted in Run.workplan["links"]
_lock = threading.Lock()


def new_run(company_id: str, kind: str, scenario_id: str | None = None, *, run_id: str | None = None) -> str:
    run_id = run_id or str(uuid.uuid4())
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
    repo.update_run(run_id, workplan={"workstreams": ws, "links": _links.get(run_id, {})},
                    budget=budget_mod.for_run(run_id).to_dict())


def start(company_id: str, kind: str, fn: Callable[[str], str], *, scenario_id: str | None = None,
          run_id: str | None = None, background: bool = True) -> str:
    """fn(run_id) -> final status ('done' | 'partial' | 'failed'). Runs inside a RunCtx."""
    run_id = run_id or new_run(company_id, kind, scenario_id)

    def _go():
        status, err = "failed", ""
        from odin.core.telemetry import span
        with run_ctx(company_id, run_id=run_id, scenario_id=scenario_id, agent="odin"), span(f"odin:run:{kind}"):
            try:
                status = fn(run_id) or "done"
            except Exception as e:   # noqa: BLE001
                log.exception("run %s failed", run_id)
                err = f"{type(e).__name__}: {e}"[:1000]
            if kind in ("analysis", "update", "report"):
                try:
                    snapshot_report(company_id, run_id, kind)
                except Exception:   # noqa: BLE001
                    log.exception("report snapshot for %s failed", run_id)
        b = budget_mod.release(run_id)
        repo.update_run(run_id, status=status, error=err, budget=b, finished_at=datetime.utcnow(),
                        trace_url=_trace_url(run_id))
        with _lock:
            _plans.pop(run_id, None)
            _links.pop(run_id, None)
        from odin.core.hooks import HOOKS   # run-end signal for the live eval scorer (odin.evals)
        HOOKS.record("run", kind, None, {"status": status, "error": err, "budget": b},
                     {"run_id": run_id, "company_id": company_id, "scenario_id": scenario_id})

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
    link = {k: meta[k] for k in ("event_id", "contract_id") if meta.get(k)}
    if link:
        _links[run_id] = link
        _persist(run_id)
    return {"run_id": uuid.UUID(run_id), "run_name": f"odin-{kind}", "tags": ["odin", kind],
            "metadata": {"run_kind": kind, **meta}, "configurable": {"thread_id": run_id},
            "recursion_limit": 200}


# ───────────────────────────── workflow views / run reports ─────────────────────────────
def _links_of(run: dict) -> dict:
    return (run.get("workplan") or {}).get("links") or {}


def runs_for(company_id: str, *, kind: str | None = None, contract_id: str | None = None,
             event_id: str | None = None, limit: int = 30) -> list[dict]:
    """Runs newest first; contract_id/event_id keep only runs that touched that contract/event."""
    from sqlalchemy import select
    with db() as s:
        stmt = select(Run).where(Run.company_id == company_id).order_by(Run.started_at.desc())
        if kind:
            stmt = stmt.where(Run.kind == kind)
        out = [repo.run_dict(r) for r in s.scalars(stmt).all()]
    if event_id:
        out = [r for r in out if _links_of(r).get("event_id") == event_id]
    if contract_id:
        evs = {e["id"] for e in repo.query("event", company_id=company_id) if contract_id in e.get("contract_ids", [])}

        def touches(r: dict) -> bool:
            lk = _links_of(r)
            if lk.get("contract_id") == contract_id or lk.get("event_id") in evs:
                return True
            ws = (r.get("workplan") or {}).get("workstreams") or []
            return r["kind"] in ("analysis", "report") and (not ws or any(w["contract_id"] == contract_id for w in ws))
        out = [r for r in out if touches(r)]
    return out[:limit]


def _key_finding(f: dict) -> str:
    cl = sorted({c.get("clause_number", "") for c in f.get("citations") or []})
    return f"{f.get('contract_id')}|{f.get('kind')}|{','.join(cl)}"


def _key_action(a: dict) -> str:
    return f"{a.get('contract_id')}|{a.get('kind')}|{(a.get('subject') or '').lower()[:60]}"


def current_state() -> dict:
    """Slim, diff-able picture of the company's live findings/actions/exposure (needs a run ctx)."""
    from odin.services import insights
    live = lambda x: x.get("status") not in ("withdrawn", "superseded", "rejected")   # noqa: E731
    exp = insights.exposure_summary()
    return {"findings": {_key_finding(f): {"contract_id": f.get("contract_id"), "kind": f.get("kind"),
                                           "claim": f.get("claim"), "severity": f.get("severity"),
                                           "citations": f.get("citations") or []}
                         for f in repo.query("finding") if live(f)},
            "actions": {_key_action(a): {"contract_id": a.get("contract_id"), "kind": a.get("kind"),
                                         "subject": a.get("subject"), "deadline": a.get("deadline")}
                        for a in repo.query("action") if live(a)},
            "exposure": {k: exp[k] for k in ("expected", "worst_case", "currency")}}


def diff_states(prev: dict | None, cur: dict) -> dict:
    """What changed between two current_state() snapshots (prev None = first run)."""
    if prev is None:
        return {"first_run": True, "new_findings": list(cur["findings"].values()), "resolved_findings": [],
                "new_actions": list(cur["actions"].values()), "resolved_actions": [],
                "exposure_delta": None}
    pick = lambda a, b: [a[k] for k in a if k not in b]   # noqa: E731
    pe, ce = prev["exposure"], cur["exposure"]
    return {"first_run": False,
            "new_findings": pick(cur["findings"], prev["findings"]),
            "resolved_findings": pick(prev["findings"], cur["findings"]),
            "new_actions": pick(cur["actions"], prev["actions"]),
            "resolved_actions": pick(prev["actions"], cur["actions"]),
            "exposure_delta": {"expected": round(ce["expected"] - pe["expected"], 2),
                               "worst_case": round(ce["worst_case"] - pe["worst_case"], 2),
                               "currency": ce["currency"]}}


def run_reports(company_id: str) -> list[dict]:
    """Stored per-run workflow reports, newest first."""
    from sqlalchemy import select
    from odin.db.tables import Record
    with db() as s:
        rows = s.scalars(select(Record).where(Record.company_id == company_id, Record.kind == "report_run")
                         .order_by(Record.created_at.desc())).all()
        return [r.data for r in rows]


def snapshot_report(company_id: str, run_id: str, kind: str) -> None:
    """Freeze the company report + a diff against the previous run's snapshot (call inside the run ctx)."""
    from odin.db.tables import Record
    rep = repo.get("report", "report:company")
    if not rep:
        return
    prev = next(iter(run_reports(company_id)), None)
    state = current_state()
    data = {"id": f"reportrun:{run_id}", "run_id": run_id, "run_kind": kind, "generated_at": datetime.utcnow().isoformat(),
            "previous_run_id": prev["run_id"] if prev else None,
            "diff": diff_states(prev.get("state") if prev else None, state), "state": state, "report": rep}
    with db() as s:
        s.add(Record(id=repo._pk(company_id, data["id"]), company_id=company_id, kind="report_run", run_id=run_id,
                     status=rep.get("completeness", ""), data=data))
