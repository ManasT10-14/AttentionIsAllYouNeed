"""Official pack endpoints, all tenant-scoped; mutations require an admin."""
from datetime import date
import threading
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from odin.api.deps import current_user, require_role
from odin.api.responses import PrivateAPIRoute, RedactedJSONResponse
from odin.core.context import run_ctx
from odin.db import repo
from odin.db.session import db
from odin.db.tables import Run, User
from odin.services import bundle, simulation, runs
from sqlalchemy import select

router = APIRouter(default_response_class=RedactedJSONResponse, route_class=PrivateAPIRoute)
admin = require_role("admin")
_dispatch_lock = threading.Lock()


def _idle(company_id, *, simulation_only=False):
    with db() as session:
        active = session.scalar(select(Run).where(Run.company_id == company_id, Run.kind.in_(["simulation"] if simulation_only else ["simulation", "analysis", "update"]), Run.status == "running"))
    if active:
        raise HTTPException(409, "Wait for the current analysis or simulation run to finish")


def _call(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/bundle/import")
def import_bundle(analyze: bool = False, u: User = Depends(admin)):
    return _call(bundle.import_bundle, u.company_id, analyze=analyze)


@router.get("/ledger")
def ledger(u: User = Depends(current_user)):
    with run_ctx(u.company_id):
        return bundle.ledger_as_of(repo.sim_now())


@router.get("/holidays")
def holidays(u: User = Depends(current_user)):
    with run_ctx(u.company_id):
        return repo.query("holiday")


@router.get("/simulation")
def get_simulation(u: User = Depends(current_user)):
    with run_ctx(u.company_id):
        imported = repo.get("simulation", "official:simulation")
        s = _call(simulation.state) if imported else {"initialized": False, "drops_loaded": [], "sim_now": repo.sim_now().isoformat()}
        s["initialized"] = bool(imported)
    with db() as session:
        active = session.scalars(select(Run).where(Run.company_id == u.company_id, Run.kind.in_(["simulation", "analysis", "update"]), Run.status == "running")).all()
        last = session.scalar(select(Run).where(Run.company_id == u.company_id, Run.kind == "simulation").order_by(Run.started_at.desc()))
    return {**s, "running": bool(active), "run_ids": [r.id for r in active],
            "simulation_running": any(r.kind == "simulation" for r in active),
            "active_runs": [{"id": r.id, "kind": r.kind} for r in active],
            "last_run": {"id": last.id, "status": last.status, "error": last.error} if last else None}


@router.get("/simulation/checkpoints")
def checkpoints(u: User = Depends(current_user)):
    with run_ctx(u.company_id):
        return repo.query("simulation_checkpoint")


@router.post("/simulation/drops/{n}/load")
def load_drop(n: int, u: User = Depends(admin)):
    _idle(u.company_id, simulation_only=True)
    return _call(simulation.load_drop, u.company_id, n)


class Advance(BaseModel):
    to: date


class Play(BaseModel):
    until: date | None = None


def _launch(u, target=None, one=False):
    with _dispatch_lock:
        _idle(u.company_id)
        with run_ctx(u.company_id):
            s = _call(simulation.state)
            now = repo.sim_now()
            if one:
                pending = repo.query("simulation_pending", status="queued")
                target = max(now, min((date.fromisoformat(p["event"]["occurred_at"][:10]) for p in pending), default=now))
            target = target or next((date.fromisoformat(d) for d in s["checkpoints"] if d > now.isoformat()), now)
            if target < now or target.isoformat() > s["checkpoints"][-1]:
                raise HTTPException(400, "Target must be between the current date and final checkpoint")
            if 1 not in s["drops_loaded"] or (target.isoformat() > s["checkpoints"][0] and 2 not in s["drops_loaded"]):
                raise HTTPException(400, "Load the required event drops before advancing")
        def go(rid):
            result = simulation.advance(u.company_id, target, one=one)
            if result.get("blocked_by_security"):
                return "partial"
            with run_ctx(u.company_id):
                incomplete = any(e.get("status") in ("received", "processing", "needs_review", "quarantined", "reviewing") or e.get("impact_review_required") for e in repo.query("event"))
            return "partial" if incomplete else "done"
        return {"run_id": runs.start(u.company_id, "simulation", go, background=True), "status": "running"}



@router.post("/simulation/step")
def step(u: User = Depends(admin)):
    return _launch(u, one=True)


@router.post("/simulation/play")
def play(body: Play, u: User = Depends(admin)):
    return _launch(u, body.until)


@router.post("/simulation/advance")
def advance(body: Advance, u: User = Depends(admin)):
    return _launch(u, body.to)


@router.post("/simulation/reset")
def reset(u: User = Depends(admin)):
    _idle(u.company_id)
    return _call(simulation.reset, u.company_id)


@router.post("/citations/recheck")
def recheck_citations(u: User = Depends(admin)):
    from odin.services.citation_recheck import recheck
    with run_ctx(u.company_id):
        return recheck(u.company_id)
