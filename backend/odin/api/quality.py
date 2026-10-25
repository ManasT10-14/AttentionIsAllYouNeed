"""Security + evaluation API (runtime guard log, quarantine review, live eval scores, golden suite)."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from odin import evals, security
from odin.api.deps import current_user, require_role
from odin.core.config import odin_config
from odin.core.context import run_ctx
from odin.core.hooks import HOOKS
from odin.db import repo
from odin.db.session import db
from odin.db.tables import ToolCall, User
from odin.evals import suite

router = APIRouter()
admin = require_role("admin")

# Attach the runtime suites to HOOKS when the API loads (odin.yaml security.enabled / evals.enabled).
security.install()
evals.install()


def scope(u: User):
    return run_ctx(u.company_id, agent="system", user_role=u.role)


# ───────────────────────────── security ─────────────────────────────
@router.get("/security/events", tags=["security"])
def security_events(severity: Optional[str] = None, source: Optional[str] = None, status: Optional[str] = None,
                    limit: int = 300, u: User = Depends(current_user)):
    with scope(u):
        evs = [e for e in reversed(repo.query("security_event"))
               if (not severity or e["severity"] == severity) and (not source or e["source"] == source)
               and (not status or e["status"] == status)]
    return evs[:limit]


@router.get("/security/summary", tags=["security"])
def security_summary(u: User = Depends(current_user)):
    with scope(u):
        evs = repo.query("security_event")
        quarantined = [e for e in repo.query("event") if e.get("status") == "quarantined"]
    with db() as s:
        blocked = s.scalars(select(ToolCall).where(ToolCall.company_id == u.company_id, ToolCall.blocked.is_(True))
                            .order_by(ToolCall.ts.desc()).limit(50)).all()
        blocked = [{"agent": t.agent, "tool": t.tool, "scope": t.scope, "run_id": t.run_id,
                    "summary": t.result_summary[:200], "ts": t.ts} for t in blocked]
    return {"total": len(evs), "open": sum(e["status"] in ("open", "quarantined") for e in evs),
            "by_severity": Counter(e["severity"] for e in evs), "by_source": Counter(e["source"] for e in evs),
            "by_kind": Counter(e["kind"] for e in evs), "by_action": Counter(e["action"] for e in evs),
            "quarantined_events": [{k: e.get(k) for k in ("id", "subject", "sender", "event_type", "occurred_at",
                                                          "reject_reason")} for e in quarantined],
            "blocked_tool_calls": blocked,
            "guard_enabled": any(isinstance(g, security.SecurityGuard) for g in HOOKS.guards)}


class Review(BaseModel):
    decision: Literal["release", "confirm", "dismiss"]
    note: str = ""


@router.post("/security/events/{sid}", tags=["security"])
def review_security_event(sid: str, body: Review, u: User = Depends(admin)):
    """release = admin trusts the quarantined email → run it; confirm = malicious → reject; dismiss = false positive."""
    with scope(u):
        sec = repo.get("security_event", sid)
        if not sec:
            raise HTTPException(404, "unknown security event")
        ev = repo.get("event", sec["event_id"]) if sec.get("event_id") else None
        if body.decision == "release" and not (ev and ev.get("status") == "quarantined"):
            raise HTTPException(400, "only a quarantined event can be released")
        status = {"release": "released", "confirm": "confirmed", "dismiss": "dismissed"}[body.decision]
        review = {"reviewed_by": u.email, "reviewed_at": datetime.utcnow().isoformat(), "review_note": body.note}
        siblings = [e for e in repo.query("security_event")
                    if ev and e.get("event_id") == ev["id"]] or [sec]
        for e in siblings:
            repo.set_status(e["id"], status, **review)
        run_id = None
        if ev and ev.get("status") == "quarantined":
            if body.decision == "confirm":
                repo.set_status(ev["id"], "rejected", reject_reason=f"confirmed prompt injection by {u.email}")
            elif body.decision in ("release", "dismiss"):
                from odin.core.models import Event
                from odin.graphs import event as event_graph
                from odin.services import events as events_svc
                repo.set_status(ev["id"], "processing", reject_reason=f"released by {u.email}")
                events_svc._advance_clock(u.company_id, Event.model_validate(ev))
                run_id = event_graph.run(u.company_id, ev["id"])
        return {"id": sid, "status": status, "event_id": ev["id"] if ev else None, "run_id": run_id,
                "updated": len(siblings)}


# ───────────────────────────── evals ─────────────────────────────
@router.get("/evals/runs", tags=["evals"])
def eval_runs(kind: Optional[str] = None, limit: int = 100, u: User = Depends(current_user)):
    with scope(u):
        rows = [r for r in reversed(repo.query("eval_score")) if not kind or r.get("run_kind") == kind]
    return rows[:limit]


@router.get("/evals/summary", tags=["evals"])
def eval_summary(limit: int = 50, u: User = Depends(current_user)):
    """Per metric: latest, mean, pass rate and a trend (oldest → newest) over the last `limit` scored runs."""
    with scope(u):
        rows = repo.query("eval_score")[-limit:]
    series: dict[str, list] = defaultdict(list)
    meta: dict[str, dict] = {}
    for r in rows:
        for m in r.get("metrics", []):
            name = m["name"].split(":")[0]
            meta.setdefault(name, {"category": m.get("category"), "method": m.get("method"),
                                   "threshold": m.get("threshold"), "required": m.get("required")})
            if m["status"] in ("passed", "failed") and m.get("score") is not None:
                series[name].append({"run_id": r["run_id"], "score": m["score"], "status": m["status"],
                                     "at": r.get("created_at")})
    metrics = []
    for name, info in meta.items():
        pts = series.get(name, [])
        metrics.append({"name": name, **info, "n": len(pts),
                        "latest": pts[-1]["score"] if pts else None,
                        "latest_status": pts[-1]["status"] if pts else "skipped",
                        "mean": round(sum(p["score"] for p in pts) / len(pts), 4) if pts else None,
                        "pass_rate": round(sum(p["status"] == "passed" for p in pts) / len(pts), 4) if pts else None,
                        "trend": [p["score"] for p in pts]})
    usage = [r.get("usage") or {} for r in rows]
    return {"runs": len(rows), "passed": sum(r.get("status") == "passed" for r in rows),
            "failed": sum(r.get("status") == "failed" for r in rows), "metrics": metrics,
            "usd_total": round(sum(x.get("usd", 0) for x in usage), 4),
            "latency_ms_trend": [x.get("latency_ms") for x in usage],
            "judge_enabled": bool(((odin_config().get("evals") or {}).get("judge") or {}).get("enabled"))}


class SuiteReq(BaseModel):
    config: str = "offline"
    allow_live: bool = False


@router.get("/evals/suite", tags=["evals"])
def suite_list(u: User = Depends(current_user)):
    with scope(u):
        jobs = list(reversed(repo.query("eval_suite")))[:20]
    return {"configs": suite.configs(), "jobs": jobs}


@router.post("/evals/suite", tags=["evals"])
def suite_start(req: SuiteReq, u: User = Depends(admin)):
    try:
        return suite.start(u.company_id, req.config, allow_live=req.allow_live)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))


@router.get("/evals/suite/{job_id}", tags=["evals"])
def suite_get(job_id: str, u: User = Depends(current_user)):
    job = suite.get(u.company_id, job_id)
    if not job:
        raise HTTPException(404)
    return job
