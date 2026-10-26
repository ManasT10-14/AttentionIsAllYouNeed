"""Synthesis (FR8): per-contract reports + company risk report. Structure is assembled deterministically
from the shared store (so every number is traceable); the LLM only writes the executive summary."""
from __future__ import annotations

from datetime import datetime

from odin.agents.base import agent_node, j, pmap, prompt, say
from odin.core.models import ReportSummary
from odin.core.context import current
from odin.core.budget import BudgetExceeded
from odin.core.hooks import Blocked
from odin.db import repo
from odin.llm.call import LLMFailure, structured
from odin.services import insights


def _refs(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        for c in it.get("citations", []) or ([it["citation"]] if it.get("citation") else []):
            key = (c["contract_id"], c["clause_number"], c.get("version"))
            if key in seen:
                continue
            seen.add(key)
            out.append({**c, "link": f"/viewer?contract={c['contract_id']}&v={c.get('version') or ''}"
                                     f"&clause={c['clause_number']}"})
    return out


def contract_report(cid: str, ws: dict | None, *, generate_summary: bool = True) -> dict:
    c = repo.contract(cid)
    x = insights.extraction(cid)
    tl = next((t for t in insights.timelines() if t.contract_id == cid), None)
    findings = [f for f in repo.query("finding", contract_id=cid) if f.get("status") not in ("withdrawn", "superseded")]
    actions = [a for a in repo.query("action", contract_id=cid) if a.get("status") not in ("superseded", "rejected")]
    viols = repo.query("violation", contract_id=cid)
    rep = {
        "id": f"report:{cid}", "kind": "contract", "contract_id": cid, "title": c.title if c else cid,
        "version": c.current_version if c else None, "generated_at": datetime.utcnow().isoformat(),
        "as_of": repo.sim_now().isoformat(),
        "completeness": (ws or {}).get("status", "unknown"), "gaps": (ws or {}).get("reason", ""),
        "evidence_score": (ws or {}).get("evidence"),
        "key_terms": x.model_dump(mode="json") if x else None,
        "timeline": [e.model_dump(mode="json") for e in tl.entries] if tl else [],
        "exposure": tl.exposure.model_dump(mode="json") if tl else None,
        "risks": sorted(findings, key=lambda f: -(f.get("severity", 0) * f.get("likelihood", 0))),
        "violations": viols, "actions": sorted(actions, key=lambda a: -(a.get("priority") or 0)),
        "health": insights.health(cid),
    }
    rep["references"] = _refs((rep["risks"] or []) + actions + viols +
                              [{"citation": e.get("citation")} for e in rep["timeline"] if e.get("citation")])
    rep["run_id"] = current().run_id
    rep["summary"] = _summary(rep, cid) if generate_summary else unavailable_summary("Not generated; report assembled from saved evidence.")
    rep["summary_status"] = "unavailable" if rep["summary"].get("unavailable") else "available"
    return rep


def _summary(rep: dict, cid: str) -> dict:
    slim = {k: rep[k] for k in ("title", "completeness", "gaps", "exposure", "health")}
    slim["risks"] = [{k: f.get(k) for k in ("kind", "claim", "severity", "likelihood", "status")} for f in rep["risks"][:10]]
    slim["actions"] = [{k: a.get(k) for k in ("kind", "subject", "deadline", "priority")} for a in rep["actions"][:8]]
    slim["upcoming"] = [e for e in rep["timeline"] if e["status"] in ("due", "upcoming", "missed")][:10]
    try:
        return structured("synth", ReportSummary, prompt("synth"), j(slim)[:20000], meta={"contract_id": cid}).model_dump()
    except (LLMFailure, BudgetExceeded, Blocked) as e:
        return unavailable_summary(str(e))


def unavailable_summary(reason: str) -> dict:
    return {"executive_summary": "Executive summary unavailable. Review the saved evidence, risks and actions below.",
            "key_risks": [], "recommended_next_steps": [], "unavailable": True, "reason": reason[:500]}


def _save_report(rep: dict, *, contract_id: str | None = None) -> None:
    """Store the run's own output as well as the replaceable latest report."""
    ctx = current()
    if ctx.run_id and not ctx.scenario_id:
        key = f"reportrevision:{ctx.run_id}:{contract_id or 'company'}"
        repo.put("report_revision", _R(**rep), rid=key, contract_id=contract_id,
                 status=rep["completeness"], publish=False)
    repo.put("report", _R(**rep), contract_id=contract_id, status=rep["completeness"])


def _write_contract(cid: str, ws: dict | None, *, generate_summary: bool = True) -> dict:
    # Persist the evidence before optional model work; budget exhaustion must never hide a report.
    rep = contract_report(cid, ws, generate_summary=False)
    _save_report(rep, contract_id=cid)
    if generate_summary:
        rep["summary"] = _summary(rep, cid)
        rep["summary_status"] = "unavailable" if rep["summary"].get("unavailable") else "available"
        _save_report(rep, contract_id=cid)
    return rep


@agent_node("synth")
def synthesize_contract(state: dict) -> dict:
    """One contract's report, written as soon as its workstream finishes (state['ws'] = its ws result)."""
    rep = _write_contract(state["contract_id"], state.get("ws"))
    say("synth", "all", "report", f"Saved contract report: {rep['title']}; summary {rep['summary_status']}.",
        payload={"report_ids": [rep["id"]], "result_snapshot": rep, "report_saved": True},
        contract_id=state["contract_id"])
    return {}


def _company(state: dict, reports: list[dict], results: dict) -> None:
    # The final company report always includes the entire portfolio, including untouched agreements.
    known = {r["contract_id"]: r for r in reports}
    reports = [known.get(c.contract_id) or repo.get("report", f"report:{c.contract_id}")
               or _write_contract(c.contract_id, None, generate_summary=False) for c in repo.contracts()]
    company = company_report(reports, results.get("cross"), generate_summary=False)
    _save_report(company)
    company["summary"] = _company_summary(company, reports)
    company["summary_status"] = "unavailable" if company["summary"].get("unavailable") else "available"
    company["quality"]["summary_available"] = company["summary_status"] == "available"
    _save_report(company)
    say("synth", "all", "report", f"Saved {len(reports)} contract reports and final company report; "
        f"workstreams {company['completeness']}; summary {company['summary_status']}.",
        payload={"completeness": company["completeness"], "result_snapshot": company,
                 "report_ids": [r["id"] for r in reports] + [company["id"]], "report_saved": True,
                 "summary_status": company["summary_status"]})


@agent_node("synth")
def synthesize_company(state: dict) -> dict:
    """Company report only; contract reports already exist (per-contract pipeline)."""
    results = {r["contract_id"]: r for r in state.get("ws_results", [])}
    cids = state.get("contract_ids") or [c.contract_id for c in repo.contracts()]
    reports = []
    for cid in cids:
        saved = repo.get("report", f"report:{cid}")
        reports.append(saved if saved and saved.get("run_id") == current().run_id
                       else _write_contract(cid, results.get(cid)))
    _company(state, reports, results)
    return {}


@agent_node("synth")
def synthesize(state: dict) -> dict:
    """All contract reports (parallel) + company report — used by update / refresh."""
    results = {r["contract_id"]: r for r in state.get("ws_results", [])}
    cids = state.get("contract_ids") or [c.contract_id for c in repo.contracts()]
    reports = pmap(lambda cid: _write_contract(cid, results.get(cid)), cids)   # independent → parallel
    _company(state, reports, results)
    return {}


def company_report(reports: list[dict], cross_ws: dict | None, *, generate_summary: bool = True) -> dict:
    exp = insights.exposure_summary()
    conflicts = [f for f in repo.query("finding", contract_id="cross") if f.get("status") not in ("withdrawn", "superseded")]
    statuses = [r["completeness"] for r in reports] + [(cross_ws or {}).get("status", "unknown")]
    complete = "complete" if all(s == "done" for s in statuses) else "partial"
    worst = [e.model_dump(mode="json") for t in insights.timelines() for e in t.entries
             if e.status in ("missed", "due", "upcoming") and e.amount][:60]
    rep = {"id": "report:company", "kind": "company", "generated_at": datetime.utcnow().isoformat(),
           "as_of": repo.sim_now().isoformat(), "completeness": complete,
           "workstreams": {r["contract_id"]: r["completeness"] for r in reports} | {"cross": (cross_ws or {}).get("status")},
           "leading_risks": sorted([f for r in reports for f in r.get("risks", [])],
                                   key=lambda f: -(f.get("severity", 0) * f.get("likelihood", 0)))[:10],
           "total_exposure": exp, "conflicts": conflicts, "prioritized_actions": insights.prioritized_actions()[:25],
           "worst_case_projection": sorted(worst, key=lambda e: e["date"]),
           "health": {r["contract_id"]: r["health"].get("score") for r in reports},
           "counterparties": insights.counterparties()}
    rep["references"] = _refs(conflicts + rep["leading_risks"] + rep["prioritized_actions"])
    rep["quality"] = {"summary_available": False, "contract_summary_coverage": {
        r["contract_id"]: r.get("summary_status", "unknown") for r in reports},
        "evidence_gaps": {r["contract_id"]: r.get("gaps") for r in reports if r.get("gaps")}}
    rep["run_id"] = current().run_id
    rep["summary"] = _company_summary(rep, reports) if generate_summary else unavailable_summary("Not generated; report assembled from saved evidence.")
    rep["summary_status"] = "unavailable" if rep["summary"].get("unavailable") else "available"
    rep["quality"]["summary_available"] = rep["summary_status"] == "available"
    return rep


def _company_summary(rep: dict, reports: list[dict]) -> dict:
    slim = {"exposure": rep["total_exposure"], "contracts": [
        {"contract_id": r["contract_id"], "summary": r.get("summary"), "gaps": r.get("gaps")} for r in reports],
        "leading_risks": rep.get("leading_risks", []),
        "conflicts": rep["conflicts"], "actions": rep["prioritized_actions"]}
    try:
        return structured("synth", ReportSummary, prompt("synth"), j(slim)[:25000]).model_dump()
    except (LLMFailure, BudgetExceeded, Blocked) as e:
        return unavailable_summary(str(e))


def rebuild_saved_reports(*, missing_only: bool = False) -> list[dict]:
    """Repair latest reports from stored evidence, without model calls or historical claims."""
    reports = []
    changed = False
    for c in repo.contracts():
        old = repo.get("report", f"report:{c.contract_id}") or {}
        if missing_only and old and old.get("version") == c.current_version:
            reports.append(old)
            continue
        changed = True
        reports.append(_write_contract(c.contract_id, {"status": old.get("completeness", "unknown"),
            "reason": old.get("gaps", "Workstream completion not recorded."),
            "evidence": old.get("evidence_score")}, generate_summary=False))
    if not reports or (missing_only and not changed and repo.get("report", "report:company")):
        return reports
    company = company_report(reports, None, generate_summary=False)
    company["recovery_note"] = "Rebuilt from current saved evidence; this is not a historical run snapshot."
    _save_report(company)
    return reports


class _R(dict):
    """Lets repo.put store a plain dict."""
    def model_dump(self, mode="json"):
        import json
        return json.loads(json.dumps(self, default=str))
