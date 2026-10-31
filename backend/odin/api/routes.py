"""REST API (plan §8). Every handler runs inside the caller's company scope."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from odin.api.deps import current_user, require_role
from odin.api.responses import PrivateAPIRoute, RedactedJSONResponse
from odin.core import citations
from odin.core.config import limits, odin_config
from odin.core.context import run_ctx
from odin.core.models import new_id
from odin.core.privacy import redact, redact_text
from odin.db import repo
from odin.db.session import db
from odin.db.tables import ClauseRow, Company, ContractVersion, Record, Run, ToolCall, User
from odin.email import event_parser
from odin.graphs import analysis as analysis_graph
from odin.graphs import update as update_graph
from odin.ingest.diff import diff_versions
from odin.ingest.service import ingest_company_context, ingest_contract
from odin.services import ask as ask_svc
from odin.services import events as events_svc
from odin.services import insights, report_render
from odin.tools.registry import REGISTRY, ApprovalRequired
from pydantic import BaseModel, Field
from sqlalchemy import func, select

router = APIRouter(default_response_class=RedactedJSONResponse, route_class=PrivateAPIRoute)
admin = require_role("admin")


def scope(u: User):
    return run_ctx(u.company_id, agent="system", user_role=u.role)


def _as_of(as_of: Optional[date]) -> date:
    return as_of or repo.sim_now()


# ───────────────────────────── company ─────────────────────────────
@router.post("/company/context", tags=["company"])
async def upload_context(file: UploadFile = File(...), u: User = Depends(admin)):
    content = await file.read()
    with scope(u):
        ctx = ingest_company_context(u.company_id, file.filename, content)
    return ctx.model_dump(mode="json")


# ───────────────────────────── contracts ─────────────────────────────
@router.post("/contracts", tags=["contracts"])
async def upload_contracts(files: list[UploadFile] = File(...), analyze: bool = True, u: User = Depends(admin)):
    results, new_ids, updates = [], [], []
    for f in files:
        content = await f.read()
        with scope(u):
            try:
                r = ingest_contract(u.company_id, f.filename, content)
            except Exception as e:   # malformed contracts must not break the batch (NFR3)
                results.append({"file": f.filename, "error": f"{type(e).__name__}: {e}"})
                continue
        results.append({"file": f.filename, **r.__dict__})
        if r.duplicate:
            continue
        (updates if r.is_update else new_ids).append(r)
    runs = []
    if analyze and new_ids:
        runs.append(analysis_graph.run(u.company_id, [r.contract_id for r in new_ids]))
    for r in updates if analyze else []:
        runs.append(update_graph.run(u.company_id, r.contract_id, r.previous_version, r.version))
    return {"results": results, "run_ids": runs}


@router.get("/contracts", tags=["contracts"])
def list_contracts(u: User = Depends(current_user)):
    with scope(u):
        out = []
        for c in repo.contracts():
            v = repo.version_row(c.contract_id, c.current_version)
            out.append({"contract_id": c.contract_id, "title": c.title, "type": c.type, "version": c.current_version,
                        "parties": c.meta.get("parties", []), "effective_date": c.meta.get("effective_date"),
                        "governing_law": c.meta.get("governing_law"), "status": c.status,
                        "external_id": c.meta.get("external_id"),
                        "relations": [r for r in insights.doc_relations() if c.contract_id in (r.get("from_doc"), r.get("to_doc"))],
                        "warnings": v.parse_warnings if v else [], "health": insights.health(c.contract_id),
                        "analysed": insights.extraction(c.contract_id) is not None})
        return out


@router.get("/contracts/{cid}", tags=["contracts"])
def get_contract(cid: str, u: User = Depends(current_user)):
    with scope(u):
        c = repo.contract(cid)
        if not c:
            raise HTTPException(404, "unknown contract")
        with db() as s:
            vers = s.scalars(select(ContractVersion).where(ContractVersion.company_id == u.company_id,
                                                           ContractVersion.contract_id == cid)
                             .order_by(ContractVersion.version)).all()
        x = insights.extraction(cid)
        return {"contract_id": cid, "title": c.title, "type": c.type, "meta": c.meta, "version": c.current_version,
                "versions": [{"version": v.version, "created_at": v.created_at, "warnings": v.parse_warnings,
                              "file": Path(v.file_path).name} for v in vers],
                "extraction": x.model_dump(mode="json") if x else None, "health": insights.health(cid),
                "clauses": [_clause_json(r) for r in repo.clauses(cid)]}


def _clause_json(r: ClauseRow) -> dict:
    return {"id": r.id, "number": r.number, "heading": r.heading, "text": r.text, "page": r.page,
            "clause_type": r.clause_type, "version": r.version, "bboxes": r.bboxes,
            "ref": r.ref, "parent_ref": r.parent_ref,
            "override": next((o for o in insights.clause_overrides(r.contract_id) if o.get("number") == r.number), None)}


class ContractDeleteIn(BaseModel):
    confirm_contract_id: str


@router.delete("/contracts/{cid}", tags=["contracts"])
def delete_contract(cid: str, req: ContractDeleteIn, u: User = Depends(admin)):
    from odin.services.contracts import delete_contract as remove
    with scope(u):
        return remove(u.company_id, cid, req.confirm_contract_id, u.id)


@router.get("/contracts/{cid}/versions/{v}/pdf", tags=["contracts"])
def contract_pdf(cid: str, v: int, u: User = Depends(current_user)):
    with scope(u):
        row = repo.version_row(cid, v)
    if not row:
        raise HTTPException(404)
    return FileResponse(row.pdf_path, media_type="application/pdf", filename=f"{cid}_v{v}.pdf",
                        content_disposition_type="inline")


@router.get("/contracts/{cid}/versions/{v}/original", tags=["contracts"])
def contract_original(cid: str, v: int, u: User = Depends(current_user)):
    with scope(u):
        row = repo.version_row(cid, v)
    if not row:
        raise HTTPException(404)
    return FileResponse(row.file_path, filename=f"{cid}_v{v}{Path(row.file_path).suffix}")


@router.get("/contracts/{cid}/clauses", tags=["contracts"])
def contract_clauses(cid: str, version: Optional[int] = None, u: User = Depends(current_user)):
    with scope(u):
        return [_clause_json(r) for r in repo.clauses(cid, version, current_only=version is None)]


@router.get("/contracts/{cid}/diff", tags=["contracts"])
def contract_diff(cid: str, from_: int = Query(..., alias="from"), to: int = Query(...), u: User = Depends(current_user)):
    with scope(u):
        return diff_versions(cid, from_, to, u.company_id).as_dict()


@router.get("/contracts/{cid}/lineage/{number}", tags=["contracts"])
def clause_lineage(cid: str, number: str, u: User = Depends(current_user)):
    with scope(u):
        rows = [r for r in repo.clauses(cid, current_only=False) if r.number == number]
        fnd = [f for f in repo.query("finding", contract_id=cid)
               if any(c["clause_number"] == number for c in f.get("citations", []))]
        return {"versions": [_clause_json(r) for r in sorted(rows, key=lambda r: r.version)],
                "findings": [{k: f.get(k) for k in ("id", "claim", "severity", "status", "created_at")} for f in fnd]}


@router.get("/citation/resolve", tags=["contracts"])
def resolve_citation(contract: str, clause: str, v: Optional[int] = None, u: User = Depends(current_user)):
    """Deep link target for 'View references': exact page + highlight boxes for a cited clause."""
    with scope(u):
        r = repo.clause_by_number(contract, clause, v)
        if not r:
            raise HTTPException(404, f"clause {clause} not found in {contract}")
        return {**_clause_json(r), "contract_id": contract,
                "pdf_url": f"/api/contracts/{contract}/versions/{r.version}/pdf"}


# ───────────────────────────── runs ─────────────────────────────
class AnalysisReq(BaseModel):
    contract_ids: Optional[list[str]] = None
    force: bool = False
    max_agent_calls: Optional[int] = None
    max_usd: Optional[float] = None
    max_debate_rounds: Optional[int] = None


@router.post("/runs/analysis", tags=["runs"])
def start_analysis(req: AnalysisReq, u: User = Depends(admin)):
    from odin.core import budget as budget_mod
    from odin.services import runs as runs_svc
    with scope(u):
        if not repo.contracts():
            raise HTTPException(400, "upload contracts first")
    run_id = runs_svc.new_run(u.company_id, "analysis")
    lims = {k: getattr(req, k) for k in ("max_agent_calls", "max_usd") if getattr(req, k) is not None}
    if lims:
        budget_mod.override(run_id, **lims)
    if req.max_debate_rounds is not None:
        limits()["max_debate_rounds"] = req.max_debate_rounds   # ponytail: process-wide override, fine for demo

    def go(rid: str) -> str:
        out = analysis_graph.build().invoke(
            {"company_id": u.company_id, "run_id": rid, "contract_ids": req.contract_ids or [], "force": req.force},
            config=runs_svc.graph_config(rid, "analysis", company_id=u.company_id))
        return out.get("final_status", "partial")
    runs_svc.start(u.company_id, "analysis", go, run_id=run_id)
    return {"run_id": run_id}


@router.get("/runs", tags=["runs"])
def list_runs(limit: int = 30, kind: Optional[str] = None, contract_id: Optional[str] = None,
              event_id: Optional[str] = None, u: User = Depends(current_user)):
    from odin.services import runs as runs_svc
    return runs_svc.runs_for(u.company_id, kind=kind, contract_id=contract_id, event_id=event_id, limit=limit)


@router.get("/runs/{run_id}", tags=["runs"])
def get_run(run_id: str, u: User = Depends(current_user)):
    with db() as s:
        r = s.get(Run, run_id)
        if not r or r.company_id != u.company_id:
            raise HTTPException(404)
        calls = s.scalars(select(ToolCall).where(ToolCall.run_id == run_id).order_by(ToolCall.ts)).all()
        d = repo.run_dict(r)
    return {**d, "messages": repo.messages(u.company_id, run_id),
            "tool_calls": [{"agent": t.agent, "tool": t.tool, "scope": t.scope, "ok": t.ok, "blocked": t.blocked,
                            "summary": t.result_summary[:200], "ms": round(t.duration_ms, 1), "ts": t.ts}
                           for t in calls]}


# ───────────────────────────── clock & views ─────────────────────────────
class ClockReq(BaseModel):
    sim_now: Optional[date] = None
    days: Optional[int] = None


@router.get("/clock", tags=["clock"])
def get_clock(u: User = Depends(current_user)):
    with scope(u):
        sim = repo.get("simulation", "official:simulation")
        return {"sim_now": repo.sim_now(), "real_today": date.today(),
                "simulation": {"start_date": sim["start_date"], "end_date": sim["checkpoints"][-1]} if sim else None}


@router.post("/clock", tags=["clock"])
def set_clock(req: ClockReq, u: User = Depends(admin)):
    with scope(u):
        if repo.get("simulation", "official:simulation"):
            from odin.api.pack import _launch
            target = req.sim_now or (repo.sim_now() + timedelta(days=req.days or 0))
            result = _launch(u, target)
            return {**result, "sim_now": repo.sim_now(), "requested_date": target}
    with db() as s:
        c = s.get(Company, u.company_id)
        base = c.sim_now or date.today()
        c.sim_now = req.sim_now or (base + timedelta(days=req.days or 0))
        new = c.sim_now
    from odin.core import bus
    bus.publish(u.company_id, "clock", {"sim_now": new})
    return {"sim_now": new}


@router.get("/timeline", tags=["views"])
def timeline(as_of: Optional[date] = None, contract_id: Optional[str] = None, u: User = Depends(current_user)):
    with scope(u):
        now = _as_of(as_of)
        tls = [t for t in insights.timelines(now) if not contract_id or t.contract_id == contract_id]
        entries = [e.model_dump(mode="json") for t in tls for e in t.entries]
        from odin.services.bundle import ledger_as_of
        history = [{"id": f"ledger:{i}", "date": r["date"], "contract_id": r.get("contract_id", ""),
                    "title": r.get("reference", "Payment ledger entry"), "status": r.get("status", ""),
                    "amount": {"amount": float(r["amount"]), "currency": r.get("currency", "USD")},
                    "source": "ledger", "kind": "payment", "from": r.get("from"), "to": r.get("to")}
                   for i, r in enumerate(ledger_as_of(now)) if not contract_id or r.get("contract_id") == contract_id]
        cs = [c for c in repo.contracts() if not contract_id or c.contract_id == contract_id]
        return {"as_of": now, "entries": [e for e in entries if e["scenario"] == "baseline"],
                "history": history, "projections": [e for e in entries if e["scenario"] == "worst_case"],
                "unanalysed_contracts": [c.contract_id for c in cs if not insights.extraction(c.contract_id)],
                "contracts": [{"contract_id": t.contract_id, "term_end": t.term_end, "notice_deadline": t.notice_deadline,
                               "entries": [e.model_dump(mode="json") for e in t.entries],
                               "exposure": t.exposure.model_dump(mode="json")} for t in tls]}



@router.get("/exposure", tags=["views"])
def exposure(as_of: Optional[date] = None, u: User = Depends(current_user)):
    with scope(u):
        return insights.exposure_summary(_as_of(as_of))


@router.get("/heatmap", tags=["views"])
def heatmap(as_of: Optional[date] = None, u: User = Depends(current_user)):
    with scope(u):
        return insights.heatmap(_as_of(as_of))


@router.get("/graph", tags=["views"])
def graph(u: User = Depends(current_user)):
    with scope(u):
        return insights.graph()


@router.get("/dashboard", tags=["views"])
def dashboard(as_of: Optional[date] = None, u: User = Depends(current_user)):
    """One call for the overview page (time slider refreshes this)."""
    with scope(u):
        now = _as_of(as_of)
        return {"as_of": now, "exposure": insights.exposure_summary(now), "heatmap": insights.heatmap(now),
                "alerts": insights.alerts(now)[:50],
                "health": {c.contract_id: insights.health(c.contract_id, now).get("score") for c in repo.contracts()}}


# ───────────────────────────── alerts ─────────────────────────────
class AlertUpdate(BaseModel):
    status: str                    # acknowledged | snoozed | resolved | open
    snooze_days: int = 7


@router.get("/alerts", tags=["alerts"])
def get_alerts(as_of: Optional[date] = None, include_closed: bool = False, u: User = Depends(current_user)):
    with scope(u):
        return insights.alerts(_as_of(as_of), include_closed)


@router.post("/alerts/{alert_id}", tags=["alerts"])
def update_alert(alert_id: str, body: AlertUpdate, u: User = Depends(admin)):
    if body.status not in ("acknowledged", "snoozed", "resolved", "open"):
        raise HTTPException(400, "bad status")
    with scope(u):
        cur = next((a for a in insights.alerts(include_closed=True) if a["id"] == alert_id), None)
        if not cur:
            raise HTTPException(404)
        from odin.core.models import Alert
        a = Alert.model_validate(cur)
        a.status = body.status
        a.snooze_until = repo.sim_now() + timedelta(days=body.snooze_days) if body.status == "snoozed" else None
        repo.put("alert", a, contract_id=a.contract_id)
        return a.model_dump(mode="json")


# ───────────────────────────── debate / findings / violations ─────────────────────────────
@router.get("/findings", tags=["agents"])
def findings(contract_id: Optional[str] = None, include_closed: bool = False, u: User = Depends(current_user)):
    with scope(u):
        fs = repo.query("finding", contract_id=contract_id)
        return [f for f in fs if include_closed or f.get("status") not in ("superseded",)]


@router.get("/debate", tags=["agents"])
def debate(contract_id: Optional[str] = None, run_id: Optional[str] = None, u: User = Depends(current_user)):
    with scope(u):
        msgs = [m for m in repo.messages(u.company_id, run_id, limit=800)
                if m["kind"] in ("attack", "verify", "rebut", "rule", "clarify", "extract", "timeline", "action",
                                 "event", "status", "plan", "error", "budget", "report")
                and (not contract_id or m["contract_id"] in (contract_id, None))]
        fs = [f for f in repo.query("finding", contract_id=contract_id) if f.get("status") != "superseded"]
        return {"messages": msgs, "findings": fs, "verifications": repo.query("verification"),
                "rulings": repo.query("ruling")}


@router.get("/violations", tags=["agents"])
def violations(u: User = Depends(current_user)):
    with scope(u):
        return repo.query("violation")


@router.get("/violations/{vid}", tags=["agents"])
def violation(vid: str, u: User = Depends(current_user)):
    with scope(u):
        v = repo.get("violation", vid)
        if not v:
            raise HTTPException(404)
        ev = repo.get("event", v["event_id"])
        ruling = {"status": v["status"], "rationale": v.get("ruling_rationale")}
        return {**v, "event": {k: ev.get(k) for k in ("id", "event_type", "occurred_at", "description", "amount",
                                                      "sender", "subject")} if ev else None,
                "ruling": ruling, "pdf_url": f"/api/contracts/{v['contract_id']}/versions/{v['version']}/pdf",
                "actions": [a for a in repo.query("action", contract_id=v["contract_id"])
                            if vid in (a.get("related_violation_ids") or [])]}


# ───────────────────────────── actions (human approval FR6.3) ─────────────────────────────
class ActionEdit(BaseModel):
    to: Optional[str] = None
    subject: Optional[str] = None
    body_md: Optional[str] = None


@router.get("/actions", tags=["actions"])
def list_actions(u: User = Depends(current_user)):
    with scope(u):
        return insights.prioritized_actions()


@router.get("/actions/{aid}", tags=["actions"])
def get_action(aid: str, u: User = Depends(current_user)):
    from odin.services import approvals
    with scope(u):
        a = repo.get("action", aid)
        if not a:
            raise HTTPException(404)
        return {**a, "counterfactual": insights.action_value(a), "approval_eligibility": approvals.eligibility(aid)}


@router.patch("/actions/{aid}", tags=["actions"])
def edit_action(aid: str, body: ActionEdit, u: User = Depends(admin)):
    with scope(u):
        from odin.services import approvals
        upd = {k: v for k, v in body.model_dump().items() if v is not None}
        try:
            return approvals.edit(aid, upd, reviewer=u.email)
        except ApprovalRequired as e:
            raise HTTPException(409, str(e))


@router.post("/actions/{aid}/{decision}", tags=["actions"])
def decide_action(aid: str, decision: str, u: User = Depends(admin)):
    with scope(u):
        from odin.services import approvals
        a = repo.get("action", aid)
        if not a:
            raise HTTPException(404)
        if decision == "approve":
            try:
                return approvals.approve(aid, reviewer=u.email)
            except ApprovalRequired as e:
                raise HTTPException(409, str(e))
        if decision == "reject":
            try:
                return approvals.reject(aid, reviewer=u.email)
            except ApprovalRequired as e:
                raise HTTPException(409, str(e))
        if decision == "send":
            try:
                tool, payload = approvals.action_payload(a)
                if tool != "send_gmail":
                    raise ApprovalRequired("amendment approval only permits applying its local proposal")
                REGISTRY.invoke("system", tool, payload, approval_id=aid)
            except ApprovalRequired as e:
                raise HTTPException(403, str(e))
            return repo.get("action", aid)
        if decision == "apply":
            try:
                tool, payload = approvals.action_payload(a)
                if tool != "apply_amendment":
                    raise ApprovalRequired("only amendment approvals permit applying a local proposal")
                result = REGISTRY.invoke("system", tool, payload, approval_id=aid)
            except ApprovalRequired as e:
                raise HTTPException(403, str(e))
            except ValueError as e:
                raise HTTPException(409, str(e))
            if result.get("is_update"):
                # Application is already completed and its lease released. Analysis failure
                # must not turn the applied proposal into a retryable external effect.
                try:
                    result["run_id"] = update_graph.run(u.company_id, result["contract_id"],
                        result["previous_version"], result["version"])
                except Exception:
                    result["analysis_warning"] = "Local proposal applied; automatic analysis could not start. Start analysis separately."
                    repo.set_status(aid, "applied", analysis_warning=result["analysis_warning"])
                else:
                    repo.set_status(aid, "applied", analysis_run_id=result["run_id"])
            return result
        raise HTTPException(400, "decision must be approve|reject|send|apply")


# ───────────────────────────── events / email ─────────────────────────────
class EventIn(BaseModel):
    subject: str
    body: str
    sender: str = ""


@router.get("/events", tags=["events"])
def list_events(u: User = Depends(current_user)):
    with scope(u):
        return list(reversed(repo.query("event")))


@router.post("/events", tags=["events"])
def post_event(ev: EventIn, u: User = Depends(admin)):
    """Manual fallback when Gmail is unavailable — same parser, same graph."""
    result = events_svc.receive(u.company_id, subject=ev.subject, body=ev.body, sender=ev.sender, method="manual")
    if result.get("status") == "rejected":
        raise HTTPException(422, "; ".join(dict.fromkeys(result.get("problems") or ["Event could not be parsed"])))
    return result


@router.post("/events/{event_id}/reprocess", tags=["events"])
def reprocess_event(event_id: str, u: User = Depends(admin)):
    from odin.graphs import event as event_graph
    from odin.services import runs as runs_svc
    with scope(u):
        ev = repo.get("event", event_id)
        if not ev:
            raise HTTPException(404, "Event not found")
        if ev.get("review_release_status") in ("release_pending", "release_failed"):
            raise HTTPException(409, "Security release requires manual recovery; ordinary reassessment is blocked")
        if ev.get("status") not in ("noise", "needs_review"):
            raise HTTPException(409, "Only unrelated or unresolved events can be reassessed here")
        if any(r["status"] == "running" for r in runs_svc.runs_for(u.company_id, event_id=event_id)):
            raise HTTPException(409, "This event already has a running assessment")
        repo.set_status(event_id, "processing", reject_reason="")
    return {"run_id": event_graph.run(u.company_id, event_id), "event_id": event_id}


@router.get("/email/template", tags=["events"])
def email_template(u: User = Depends(current_user)):
    return PlainTextResponse(event_parser.TEMPLATE)


@router.post("/email/poll-now", tags=["events"])
def poll_now(u: User = Depends(admin)):
    from odin.email import poller
    return poller.poll_company(u.company_id)


@router.get("/email/status", tags=["events"])
def email_status(u: User = Depends(current_user)):
    from odin.email import poller
    return poller.status(u.company_id)


# ───────────────────────────── what-if ─────────────────────────────
@router.post("/whatif", tags=["whatif"])
def whatif(ev: EventIn, u: User = Depends(admin)):
    sid = new_id("wif")
    r = events_svc.receive(u.company_id, subject=ev.subject, body=ev.body, sender="", method="manual",
                           scenario_id=sid)
    return {"scenario_id": sid, **r}


@router.get("/whatif/{sid}", tags=["whatif"])
def whatif_result(sid: str, u: User = Depends(current_user)):
    with run_ctx(u.company_id, scenario_id=sid, agent="system"):
        with db() as s:
            rows = s.scalars(select(Record).where(Record.company_id == u.company_id, Record.scenario_id == sid)).all()
            by_kind: dict = {}
            for r in rows:
                if r.kind not in {"event", "extraction", "finding", "verification", "ruling", "violation",
                                   "action", "alert", "report", "dependency", "clarification"}:
                    continue
                by_kind.setdefault(r.kind, []).append(r.data)
        run = None
        with db() as s:
            rr = s.scalars(select(Run).where(Run.company_id == u.company_id, Run.scenario_id == sid)).first()
            run = repo.run_dict(rr) if rr else None
        if not rows and not rr:
            raise HTTPException(404, "scenario not found")
        base = None
        with run_ctx(u.company_id, agent="system"):
            base = insights.exposure_summary()
        return {"scenario_id": sid, "run": run, "records": by_kind, "exposure_base": base,
                "exposure_scenario": insights.exposure_summary(),
                "messages": [m for m in repo.messages(u.company_id, rr.id if rr else None)] if rr else []}


@router.delete("/whatif/{sid}", tags=["whatif"])
def whatif_drop(sid: str, u: User = Depends(admin)):
    with scope(u):
        with db() as session:
            owned = session.scalar(select(Record.id).where(Record.company_id == u.company_id, Record.scenario_id == sid))
            run = session.scalar(select(Run.id).where(Run.company_id == u.company_id, Run.scenario_id == sid))
        if not owned and not run:
            raise HTTPException(404, "scenario not found")
        repo.drop_scenario(sid)
    return {"dropped": sid}


# ───────────────────────────── ask / reports / insights ─────────────────────────────
class AskTurn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    contract_ids: list[str] = Field(default_factory=list, max_length=50)


class AskReq(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    contract_ids: Optional[list[str]] = Field(default=None, max_length=50)
    history: list[AskTurn] = Field(default_factory=list, max_length=4)


@router.post("/ask", tags=["ask"])
def ask(req: AskReq, u: User = Depends(current_user)):
    if not req.question.strip():
        raise HTTPException(400, "Enter a question.")
    return ask_svc.ask(u.company_id, req.question.strip(), req.contract_ids, [turn.model_dump() for turn in req.history])


@router.get("/reports/{which}", tags=["reports"])
def report(which: str, contract_id: Optional[str] = None, format: str = "json", u: User = Depends(current_user)):
    with scope(u):
        rid = "report:company" if which == "company" else f"report:{contract_id}"
        r = repo.get("report", rid)
        if not r:
            raise HTTPException(404, "report not generated yet — run an analysis")
        r = redact(r)
        if format == "json":
            return r
        body = report_render.company_html(r) if which == "company" else report_render.contract_html(r)
        if format == "html":
            return HTMLResponse(f"<html><body style='font-family:sans-serif;max-width:900px;margin:auto'>{body}</body></html>")
        return Response(report_render.to_pdf(body), media_type="application/pdf",
                        headers={"content-disposition": f"attachment; filename={rid.replace(':', '_')}.pdf"})


@router.post("/reports/refresh", tags=["reports"])
def refresh_reports(u: User = Depends(admin), contract_id: Optional[str] = None):
    from odin.agents import synth
    from odin.graphs import analysis
    from odin.services import runs as runs_svc

    with scope(u):
        cids = [contract_id] if contract_id else [c.contract_id for c in repo.contracts()]
        if not cids or any(not repo.contract(cid) for cid in cids):
            raise HTTPException(404, "No matching contracts to generate reports for")
        missing = [cid for cid in cids if not insights.extraction(cid)]
    if missing:
        # Synthesis cannot replace missing extraction/review. Run the actual analysis first.
        return {"run_id": analysis.run(u.company_id, contract_ids=cids), "mode": "analysis",
                "reason": "Missing contract analysis; extracting and reviewing before synthesis."}

    def go(rid: str) -> str:
        cached = []
        for cid in cids:
            saved = repo.get("report", f"report:{cid}") or {}
            status = saved.get("completeness")
            cached.append({"contract_id": cid, "status": status if status in ("done", "partial", "failed") else "partial",
                           "reason": saved.get("gaps") or ("Original workstream completion not recorded." if status not in ("done", "partial", "failed") else ""),
                           "evidence": saved.get("evidence_score")})
        result = synth.synthesize({"company_id": u.company_id, "run_id": rid,
                                  "contract_ids": cids, "ws_results": cached})
        return "partial" if result.get("errors") or result.get("budget_hit") else "done"
    return {"run_id": runs_svc.start(u.company_id, "report", go), "mode": "synthesis"}


@router.get("/insights/health", tags=["insights"])
def health_all(u: User = Depends(current_user)):
    with scope(u):
        return [insights.health(c.contract_id) for c in repo.contracts()]


@router.get("/insights/calibration", tags=["insights"])
def calibration(u: User = Depends(current_user)):
    with scope(u):
        return insights.calibration()


@router.get("/insights/counterparties", tags=["insights"])
def counterparties(u: User = Depends(current_user)):
    with scope(u):
        return insights.counterparties()


@router.get("/export/calendar.ics", tags=["export"])
def export_ics(u: User = Depends(current_user)):
    with scope(u):
        return Response(redact_text(insights.ics()), media_type="text/calendar",
                        headers={"content-disposition": "attachment; filename=odin-deadlines.ics"})


@router.get("/export/actions.csv", tags=["export"])
def export_csv(u: User = Depends(current_user)):
    with scope(u):
        return Response(redact_text(insights.actions_csv()), media_type="text/csv",
                        headers={"content-disposition": "attachment; filename=odin-actions.csv"})


class OwnerReq(BaseModel):
    timeline_id: str
    owner: str


@router.post("/owners", tags=["insights"])
def set_owner(req: OwnerReq, u: User = Depends(admin)):
    with scope(u):
        cur = insights.owners()
        cur[req.timeline_id] = req.owner
        from odin.agents.synth import _R
        repo.put("owners", _R(id=f"owners:{u.company_id}", map=cur))
        return cur


@router.post("/digest/draft", tags=["insights"])
def digest(u: User = Depends(admin)):
    """Daily risk digest → drafted as an action (admin approves → send via Gmail)."""
    from odin.core.models import ActionDraft
    with scope(u):
        now = repo.sim_now()
        al = insights.alerts(now)[:15]
        exp = insights.exposure_summary(now)
        own = insights.owners()
        lines = [f"Odin risk digest — {now}", "",
                 f"Exposure: expected {exp['currency']} {exp['expected']:,.0f}, worst case {exp['worst_case']:,.0f}", "",
                 "Open alerts:"] + [f"- [{a['severity'].upper()}] {a['contract_id'] or ''}: {a['title']} "
                                   f"(due {a.get('due_date') or '-'})" for a in al]
        if own:
            lines += ["", f"{len(own)} obligations have owners assigned."]
        ctx = (repo.company(u.company_id).context or {})
        a = ActionDraft(id=new_id("act"), contract_id="cross", kind="escalation_memo",
                        to=", ".join(ctx.get("contacts") or [u.email]), subject=f"Odin risk digest {now}",
                        body_md="\n".join(lines), citations=[], confidence=1.0, needs_human_approval=True, priority=1)
        repo.put("action", a, contract_id="cross")
        return a.model_dump(mode="json")


# ───────────────────────────── observability / tools / demo ─────────────────────────────
@router.get("/observability", tags=["observability"])
def observability(u: User = Depends(current_user)):
    with db() as s:
        tc = s.execute(select(ToolCall.agent, ToolCall.tool, func.count())
                       .where(ToolCall.company_id == u.company_id)
                       .group_by(ToolCall.agent, ToolCall.tool)).all()
        blocked = s.scalar(select(func.count()).select_from(ToolCall).where(ToolCall.company_id == u.company_id,
                                                                           ToolCall.blocked.is_(True)))
        runs = s.scalars(select(Run).where(Run.company_id == u.company_id).order_by(Run.started_at.desc()).limit(15)).all()
        run_list = [repo.run_dict(r) for r in runs]
    with scope(u):
        cits = [c for k in ("finding", "action", "violation") for r in repo.query(k) for c in r.get("citations", [])]
        unverified = sum(1 for c in cits if not c.get("verified"))
    return {"runs": run_list, "tool_usage": [{"agent": a, "tool": t, "calls": n} for a, t, n in tc],
            "blocked_tool_calls": blocked, "citation_guard": {**citations.stats(), "stored_citations": len(cits),
                                                             "stored_unverified": unverified},
            "limits": limits(), "providers": odin_config()["defaults"]}


@router.get("/tools", tags=["observability"])
def tools(u: User = Depends(current_user)):
    return REGISTRY.describe()


@router.post("/demo/seed", tags=["demo"])
def demo_seed(analyze: bool = True, u: User = Depends(admin)):
    from odin.services import demo
    return demo.seed(u.company_id, analyze=analyze)


@router.post("/workspace/reset", tags=["demo"])
def workspace_reset(u: User = Depends(admin)):
    """Delete this company's contracts, events and analysis; keep users and the Gmail link."""
    import shutil

    from odin.core.config import DATA_DIR
    from odin.db.tables import AgentMessageRow, Contract
    from sqlalchemy import delete
    cid = u.company_id
    with db() as s:
        s.scalar(select(Company).where(Company.id == cid).with_for_update())
        if s.scalar(select(Record.id).where(Record.company_id == cid, Record.kind == "action",
                    Record.data["approval_execution"]["state"].as_string() == "executing").limit(1)):
            raise HTTPException(409, "An action is executing; reconcile or wait before resetting the workspace")
        for t in (ToolCall, AgentMessageRow, Run, Record, ClauseRow, ContractVersion, Contract):
            s.execute(delete(t).where(t.company_id == cid))
        co = s.get(Company, cid)
        co.context, co.sim_now, co.name = {}, None, u.email.split("@")[-1]
    shutil.rmtree(DATA_DIR / cid, ignore_errors=True)
    return {"ok": True}


@router.post("/demo/play", tags=["demo"])
def demo_play(delay_seconds: float = 20, u: User = Depends(admin)):
    from odin.services import demo
    return demo.play(u.company_id, delay_seconds)
