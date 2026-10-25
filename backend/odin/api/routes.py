"""REST API (plan §8). Every handler runs inside the caller's company scope."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy import func, select

from odin.api.deps import current_user, require_role
from odin.core import citations
from odin.core.config import limits, odin_config
from odin.core.context import run_ctx
from odin.core.models import new_id
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

router = APIRouter()
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
            "clause_type": r.clause_type, "version": r.version, "bboxes": r.bboxes}


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
def list_runs(limit: int = 30, u: User = Depends(current_user)):
    with db() as s:
        rows = s.scalars(select(Run).where(Run.company_id == u.company_id).order_by(Run.started_at.desc()).limit(limit)).all()
        return [repo.run_dict(r) for r in rows]


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
        return {"sim_now": repo.sim_now(), "real_today": date.today()}


@router.post("/clock", tags=["clock"])
def set_clock(req: ClockReq, u: User = Depends(current_user)):
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
        return {"as_of": now, "contracts": [
            {"contract_id": t.contract_id, "term_end": t.term_end, "notice_deadline": t.notice_deadline,
             "entries": [e.model_dump(mode="json") for e in t.entries], "exposure": t.exposure.model_dump(mode="json")}
            for t in insights.timelines(now) if not contract_id or t.contract_id == contract_id]}


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
def update_alert(alert_id: str, body: AlertUpdate, u: User = Depends(current_user)):
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
    with scope(u):
        a = repo.get("action", aid)
        if not a:
            raise HTTPException(404)
        return {**a, "counterfactual": insights.action_value(a)}


@router.patch("/actions/{aid}", tags=["actions"])
def edit_action(aid: str, body: ActionEdit, u: User = Depends(admin)):
    with scope(u):
        a = repo.get("action", aid)
        if not a or a["status"] not in ("draft",):
            raise HTTPException(400, "only drafts can be edited")
        upd = {k: v for k, v in body.model_dump().items() if v is not None}
        return repo.set_status(aid, "draft", **upd, edited_by=u.email)


@router.post("/actions/{aid}/{decision}", tags=["actions"])
def decide_action(aid: str, decision: str, u: User = Depends(admin)):
    with scope(u):
        a = repo.get("action", aid)
        if not a:
            raise HTTPException(404)
        if decision == "approve":
            return repo.set_status(aid, "approved", approved_by=u.email, approved_at=datetime.utcnow().isoformat())
        if decision == "reject":
            return repo.set_status(aid, "rejected", rejected_by=u.email)
        if decision == "send":
            if "@" not in (a.get("to") or ""):
                raise HTTPException(400, "recipient is not an email address — edit 'to' first")
            try:
                r = REGISTRY.invoke("system", "send_gmail", {"to": a["to"], "subject": a["subject"],
                                                             "body": a["body_md"]}, approval_id=aid)
            except ApprovalRequired as e:
                raise HTTPException(403, str(e))
            return repo.set_status(aid, "sent", sent_at=datetime.utcnow().isoformat(), gmail=r)
        if decision == "apply":
            try:
                return REGISTRY.invoke("system", "apply_amendment", {"action_id": aid}, approval_id=aid)
            except ApprovalRequired as e:
                raise HTTPException(403, str(e))
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
def post_event(ev: EventIn, u: User = Depends(current_user)):
    """Manual fallback when Gmail is unavailable — same parser, same graph."""
    return events_svc.receive(u.company_id, subject=ev.subject, body=ev.body, sender=ev.sender, method="manual")


@router.get("/email/template", tags=["events"])
def email_template(u: User = Depends(current_user)):
    return PlainTextResponse(event_parser.TEMPLATE)


@router.post("/email/poll-now", tags=["events"])
def poll_now(u: User = Depends(current_user)):
    from odin.email import poller
    return poller.poll_company(u.company_id)


@router.get("/email/status", tags=["events"])
def email_status(u: User = Depends(current_user)):
    from odin.email import poller
    return poller.status(u.company_id)


# ───────────────────────────── what-if ─────────────────────────────
@router.post("/whatif", tags=["whatif"])
def whatif(ev: EventIn, u: User = Depends(current_user)):
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
                by_kind.setdefault(r.kind, []).append(r.data)
        run = None
        with db() as s:
            rr = s.scalars(select(Run).where(Run.scenario_id == sid)).first()
            run = repo.run_dict(rr) if rr else None
        base = None
        with run_ctx(u.company_id, agent="system"):
            base = insights.exposure_summary()
        return {"scenario_id": sid, "run": run, "records": by_kind, "exposure_base": base,
                "exposure_scenario": insights.exposure_summary(),
                "messages": [m for m in repo.messages(u.company_id, rr.id if rr else None)] if rr else []}


@router.delete("/whatif/{sid}", tags=["whatif"])
def whatif_drop(sid: str, u: User = Depends(current_user)):
    repo.drop_scenario(sid)
    return {"dropped": sid}


# ───────────────────────────── ask / reports / insights ─────────────────────────────
class AskReq(BaseModel):
    question: str
    contract_ids: Optional[list[str]] = None


@router.post("/ask", tags=["ask"])
def ask(req: AskReq, u: User = Depends(current_user)):
    return ask_svc.ask(u.company_id, req.question, req.contract_ids)


@router.get("/reports/{which}", tags=["reports"])
def report(which: str, contract_id: Optional[str] = None, format: str = "json", u: User = Depends(current_user)):
    with scope(u):
        rid = "report:company" if which == "company" else f"report:{contract_id}"
        r = repo.get("report", rid)
        if not r:
            raise HTTPException(404, "report not generated yet — run an analysis")
        if format == "json":
            return r
        body = report_render.company_html(r) if which == "company" else report_render.contract_html(r)
        if format == "html":
            return HTMLResponse(f"<html><body style='font-family:sans-serif;max-width:900px;margin:auto'>{body}</body></html>")
        return Response(report_render.to_pdf(body), media_type="application/pdf",
                        headers={"content-disposition": f"attachment; filename={rid.replace(':', '_')}.pdf"})


@router.post("/reports/refresh", tags=["reports"])
def refresh_reports(u: User = Depends(current_user)):
    from odin.agents import synth
    from odin.services import runs as runs_svc

    def go(rid: str) -> str:
        cached = {}
        for w in (repo.get("report", f"report:{c.contract_id}") or {} for c in repo.contracts()):
            if w:
                cached[w["contract_id"]] = {"contract_id": w["contract_id"], "status": w.get("completeness"),
                                            "reason": w.get("gaps"), "evidence": w.get("evidence_score")}
        synth.synthesize({"company_id": u.company_id, "run_id": rid, "ws_results": list(cached.values())})
        return "done"
    return {"run_id": runs_svc.start(u.company_id, "report", go)}


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
        return Response(insights.ics(), media_type="text/calendar",
                        headers={"content-disposition": "attachment; filename=odin-deadlines.ics"})


@router.get("/export/actions.csv", tags=["export"])
def export_csv(u: User = Depends(current_user)):
    with scope(u):
        return Response(insights.actions_csv(), media_type="text/csv",
                        headers={"content-disposition": "attachment; filename=odin-actions.csv"})


class OwnerReq(BaseModel):
    timeline_id: str
    owner: str


@router.post("/owners", tags=["insights"])
def set_owner(req: OwnerReq, u: User = Depends(current_user)):
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
    from sqlalchemy import delete
    from odin.core.config import DATA_DIR
    from odin.db.tables import AgentMessageRow, Contract
    cid = u.company_id
    with db() as s:
        for t in (ToolCall, AgentMessageRow, Run, Record, ClauseRow, ContractVersion, Contract):
            s.execute(delete(t).where(t.company_id == cid))
        co = s.get(Company, cid)
        co.context, co.sim_now, co.name = {}, None, u.email.split("@")[-1]
    shutil.rmtree(DATA_DIR / cid, ignore_errors=True)
    return {"ok": True}


@router.post("/demo/play", tags=["demo"])
def demo_play(delay_seconds: float = 20, u: User = Depends(current_user)):
    from odin.services import demo
    return demo.play(u.company_id, delay_seconds)
