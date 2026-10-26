"""Workflow-execution view (per run) + event / run reports. Read-side over runs, messages, tool_calls, records."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select

from odin.api.deps import current_user
from odin.api.routes import scope
from odin.db import repo
from odin.db.session import db
from odin.db.tables import Record, Run, ToolCall, User, AgentMessageRow
from odin.services import report_render, runs as runs_svc

router = APIRouter()
OUT_KINDS = ("finding", "alert", "action", "violation")


def _run(u: User, run_id: str) -> dict:
    with db() as s:
        r = s.get(Run, run_id)
        if not r or r.company_id != u.company_id:
            raise HTTPException(404, "run not found")
        return repo.run_dict(r)


def _secs(a: str, b: str) -> float:
    return round((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds(), 1)


def _timeline(u: User, run: dict) -> dict:
    msgs = repo.messages(u.company_id, run["id"])
    with db() as s:
        calls = [{"agent": t.agent, "tool": t.tool, "ok": t.ok, "blocked": t.blocked, "ms": round(t.duration_ms, 1),
                  "summary": t.result_summary[:160], "ts": t.ts.isoformat()}
                 for t in s.scalars(select(ToolCall).where(ToolCall.run_id == run["id"]).order_by(ToolCall.ts)).all()]
    steps, last = [], {}
    for m in msgs:    # a message is posted when an agent finishes a step: it ran since the previous message of that contract
        start = last.get(m["contract_id"]) or last.get(None) or run["started_at"]
        steps.append({**{k: m[k] for k in ("id", "sender", "receiver", "kind", "summary", "contract_id")},
                      "started_at": start, "ended_at": m["ts"], "duration_s": max(0, _secs(start, m["ts"])),
                      "tool_calls": [c for c in calls if c["agent"] == m["sender"] and start < c["ts"] <= m["ts"]]})
        last[m["contract_id"]] = last[None] = m["ts"]
    running = run["status"] == "running"
    last = msgs[-1] if msgs else None
    current = None
    if running:
        current = last["receiver"] if last and last["receiver"] not in ("all", "") else (last["sender"] if last else "odin")
    return {"steps": steps, "tool_call_count": len(calls), "running": running, "current_agent": current,
            "agents": (run["budget"] or {}).get("per_agent", {})}


def _outputs(u: User, run: dict) -> dict:
    ev = runs_svc._links_of(run).get("event_id")
    out = {}
    for k in OUT_KINDS:
        with db() as s:     # Record.run_id is the last run that wrote the record
            owner = {r.data.get("id"): r.run_id for r in s.scalars(
                select(Record).where(Record.company_id == u.company_id, Record.kind == k, Record.scenario_id.is_(None)))}
        out[k] = [r for r in repo.query(k) if (ev and r.get("event_id") == ev) or owner.get(r.get("id")) == run["id"]]
    return out


@router.get("/workflow/{run_id}", tags=["workflow"])
def workflow(run_id: str, u: User = Depends(current_user)):
    run = _run(u, run_id)
    with scope(u):
        outs = _outputs(u, run)
        vers, rulings = repo.query("verification"), repo.query("ruling")
        debate = [{"finding": f, "verifications": [v for v in vers if v.get("finding_id") == f["id"]],
                   "ruling": next((r for r in rulings if r.get("finding_id") == f["id"]), None)}
                  for f in outs["finding"]]
    ws = (run["workplan"] or {}).get("workstreams") or []
    snap = next((r for r in runs_svc.run_reports(u.company_id) if r["run_id"] == run_id), None)
    ev = runs_svc._links_of(run).get("event_id")
    gaps = [{"contract_id": w["contract_id"], "status": w["status"], "reason": w.get("reason", "")}
            for w in ws if w["status"] != "done"]
    reports = ([{"kind": "run", "title": "Workflow report", "path": f"/api/reports/runs/{run_id}"}] if snap else []) \
        + ([{"kind": "event", "title": "Event report", "path": f"/api/reports/events/{ev}"}] if ev else [])
    return {"run": run, "event_id": ev, "contract_id": runs_svc._links_of(run).get("contract_id"),
            "workstreams": ws, "timeline": _timeline(u, run), "debate": debate, "outputs": outs,
            "remarks": {"decision": run["status"], "complete": run["status"] == "done", "gaps": gaps,
                        "error": run["error"], "report_completeness": ((snap or {}).get("report") or {}).get("completeness")},
            "reports": reports, "trace_url": run["trace_url"]}


# ───────────────────────────── reports ─────────────────────────────
def _respond(r: dict, html_fn, name: str, format: str):
    if format == "json":
        return r
    body = html_fn(r)
    if format == "html":
        return HTMLResponse(f"<html><body style='font-family:sans-serif;max-width:900px;margin:auto'>{body}</body></html>")
    return Response(report_render.to_pdf(body), media_type="application/pdf",
                    headers={"content-disposition": f"attachment; filename={name}.pdf"})


def event_report(company_id: str, event_id: str) -> dict:
    ev = repo.get("event", event_id)
    if not ev:
        raise HTTPException(404, "event not found")

    def mine(k):
        return [x for x in repo.query(k) if x.get("event_id") == event_id]
    viol, alerts, actions, findings = mine("violation"), mine("alert"), mine("action"), mine("finding")
    fids = {f["id"] for f in findings}
    rulings = [r for r in repo.query("ruling") if r.get("finding_id") in fids]
    cites, seen = [], set()
    for x in viol + alerts + actions:
        own = [{"contract_id": x["contract_id"], "clause_number": x["clause_number"], "quote": x.get("quote"),
                "page": x.get("page"), "version": x.get("version"), "verified": True}] if x.get("clause_number") else []
        for c in x.get("citations") or own:
            k = (c.get("contract_id"), c.get("clause_number"))
            if k not in seen:
                seen.add(k)
                cites.append({**c, "link": f"/viewer?contract={c.get('contract_id')}&clause={c.get('clause_number')}"})
    amounts = [v["exposure"] for v in viol if v.get("exposure")]
    return {"id": f"report:event:{event_id}", "kind": "event", "event": ev,
            "run_ids": [r["id"] for r in runs_svc.runs_for(company_id, event_id=event_id)],
            "affected_contracts": ev.get("contract_ids", []), "affected_clauses": cites,
            "violations": viol, "alerts": alerts, "actions": actions, "rulings": rulings, "findings": findings,
            "exposure_delta": {"amount": round(sum(a["amount"] for a in amounts), 2),
                               "currency": amounts[0]["currency"]} if amounts else None,
            "references": cites}


@router.get("/reports/events/{event_id}", tags=["reports"])
def get_event_report(event_id: str, format: str = "json", u: User = Depends(current_user)):
    with scope(u):
        r = event_report(u.company_id, event_id)
    return _respond(r, report_render.event_html, f"event_{event_id}", format)


@router.get("/reports/runs/{run_id}", tags=["reports"])
def get_run_report(run_id: str, format: str = "json", u: User = Depends(current_user)):
    r = next((x for x in runs_svc.run_reports(u.company_id) if x["run_id"] == run_id), None)
    if not r:
        raise HTTPException(404, "no workflow report for this run")
    return _respond(r, report_render.run_html, f"run_{run_id[:8]}", format)


@router.get("/report-index", tags=["reports"])
def report_index(u: User = Depends(current_user)):
    """All three report kinds, newest first, each with run id + date."""
    with db() as s:
        rows = s.scalars(select(Record).where(Record.company_id == u.company_id, Record.kind == "report",
                                              Record.scenario_id.is_(None)).order_by(Record.updated_at.desc())).all()
        contracts = [{"contract_id": r.contract_id, "title": r.data.get("title"), "version": r.data.get("version"),
                      "completeness": r.data.get("completeness"), "run_id": r.run_id,
                      "generated_at": r.data.get("generated_at")} for r in rows if r.contract_id]
    with scope(u):
        known = {c["contract_id"] for c in contracts}
        contracts.extend({"contract_id": c.contract_id, "title": c.title, "version": c.current_version,
                          "completeness": "not_generated", "run_id": None, "generated_at": None}
                         for c in repo.contracts() if c.contract_id not in known)
        events = [{"event_id": e["id"], "subject": e.get("subject"), "event_type": e.get("event_type"),
                   "status": e.get("status"), "contract_ids": e.get("contract_ids", []), "date": e.get("occurred_at"),
                   "run_ids": [r["id"] for r in runs_svc.runs_for(u.company_id, event_id=e["id"])]}
                  for e in reversed(repo.query("event"))]
    runs = [{"run_id": r["run_id"], "run_kind": r["run_kind"], "generated_at": r["generated_at"],
             "completeness": r["report"].get("completeness"), "previous_run_id": r["previous_run_id"],
             "new_findings": len(r.get("diff", {}).get("new_findings", [])), "resolved_findings": len(r.get("diff", {}).get("resolved_findings", []))}
            for r in runs_svc.run_reports(u.company_id)]
    return {"contracts": contracts, "events": events, "runs": runs}


@router.get("/agent-messages/{message_id}/result", tags=["agents"])
def message_result(message_id: str, u: User = Depends(current_user)):
    with db() as session:
        row = session.get(AgentMessageRow, message_id)
        if not row or row.company_id != u.company_id:
            raise HTTPException(404, "message not found")
        payload = row.payload or {}
        if payload.get("contribution"):
            return payload["contribution"]
        sender, kind, cid, run_id = row.sender, row.kind, row.contract_id, row.run_id
    from odin.services.message_results import capture_result
    from odin.core.context import run_ctx
    with scope(u), run_ctx(run_id=run_id):
        if sender == "synth" and not payload.get("result_snapshot"):
            snapshot = repo.get("report_run", f"reportrun:{run_id}")
            report = (snapshot or {}).get("report")
            if not report:
                return {"source": "unavailable", "sections": [],
                        "notice": "No historical Synth report was saved for this message's run. The latest company report is available separately."}
            if cid:
                report = next((r for r in snapshot.get("contract_reports", []) if r.get("contract_id") == cid), None)
                if not report:
                    return {"source": "unavailable", "sections": [],
                            "notice": "No historical contract report was saved for this run."}
            payload = {**payload, "result_snapshot": report}
        result = capture_result(sender, kind, cid, payload)
    if sender == "odin" and not result["sections"]:
        run = _run(u, run_id)
        result["sections"] = [{"title": "Persisted run work plan and completion gaps",
                               "value": run.get("workplan") or {}}]
    result["source"] = "available_records"
    result["notice"] = "Loaded from available records. These records may have changed since this message; no message-time snapshot was saved."
    return result
