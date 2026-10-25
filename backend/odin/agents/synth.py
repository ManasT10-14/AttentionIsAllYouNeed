"""Synthesis (FR8): per-contract reports + company risk report. Structure is assembled deterministically
from the shared store (so every number is traceable); the LLM only writes the executive summary."""
from __future__ import annotations

from datetime import datetime

from odin.agents.base import agent_node, j, pmap, prompt, say
from odin.core.models import ReportSummary
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


def contract_report(cid: str, ws: dict | None) -> dict:
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
    rep["summary"] = _summary(rep, cid)
    return rep


def _summary(rep: dict, cid: str) -> dict:
    slim = {k: rep[k] for k in ("title", "completeness", "gaps", "exposure", "health")}
    slim["risks"] = [{k: f.get(k) for k in ("kind", "claim", "severity", "likelihood", "status")} for f in rep["risks"][:10]]
    slim["actions"] = [{k: a.get(k) for k in ("kind", "subject", "deadline", "priority")} for a in rep["actions"][:8]]
    slim["upcoming"] = [e for e in rep["timeline"] if e["status"] in ("due", "upcoming", "missed")][:10]
    try:
        return structured("synth", ReportSummary, prompt("synth"), j(slim)[:20000], meta={"contract_id": cid}).model_dump()
    except LLMFailure as e:
        return {"executive_summary": f"(summary unavailable: {e})", "key_risks": [], "recommended_next_steps": []}


@agent_node("synth")
def synthesize(state: dict) -> dict:
    results = {r["contract_id"]: r for r in state.get("ws_results", [])}
    cids = state.get("contract_ids") or [c.contract_id for c in repo.contracts()]

    def one(cid):
        rep = contract_report(cid, results.get(cid))
        repo.put("report", _R(**rep), contract_id=cid, status=rep["completeness"])
        return rep
    reports = pmap(one, cids)            # independent summaries → parallel (was ~23 s × N serial)
    company = company_report(reports, results.get("cross"))
    repo.put("report", _R(**company), status=company["completeness"])
    say("synth", "all", "report", f"Reports ready: {len(reports)} contract reports + company risk report "
        f"({company['completeness'].upper()}).", payload={"completeness": company["completeness"]})
    return {}


def company_report(reports: list[dict], cross_ws: dict | None) -> dict:
    exp = insights.exposure_summary()
    conflicts = [f for f in repo.query("finding", contract_id="cross") if f.get("status") not in ("withdrawn", "superseded")]
    statuses = [r["completeness"] for r in reports] + [(cross_ws or {}).get("status", "unknown")]
    complete = "complete" if all(s == "done" for s in statuses) else "partial"
    worst = [e.model_dump(mode="json") for t in insights.timelines() for e in t.entries
             if e.status in ("missed", "due", "upcoming") and e.amount][:60]
    rep = {"id": "report:company", "kind": "company", "generated_at": datetime.utcnow().isoformat(),
           "as_of": repo.sim_now().isoformat(), "completeness": complete,
           "workstreams": {r["contract_id"]: r["completeness"] for r in reports} | {"cross": (cross_ws or {}).get("status")},
           "total_exposure": exp, "conflicts": conflicts, "prioritized_actions": insights.prioritized_actions()[:25],
           "worst_case_projection": sorted(worst, key=lambda e: e["date"]),
           "health": {r["contract_id"]: r["health"].get("score") for r in reports},
           "counterparties": insights.counterparties()}
    rep["references"] = _refs(conflicts + rep["prioritized_actions"])
    slim = {"exposure": {k: exp[k] for k in ("expected", "worst_case", "currency")},
            "contracts": [{k: r[k] for k in ("contract_id", "completeness")} | {"summary": r["summary"]["executive_summary"]}
                          for r in reports],
            "conflicts": [{k: f.get(k) for k in ("claim", "severity", "other_contract_ids")} for f in conflicts],
            "top_actions": [{k: a.get(k) for k in ("contract_id", "kind", "subject", "deadline")} for a in rep["prioritized_actions"][:10]]}
    try:
        rep["summary"] = structured("synth", ReportSummary, prompt("synth"), j(slim)[:25000]).model_dump()
    except LLMFailure as e:
        rep["summary"] = {"executive_summary": f"(summary unavailable: {e})", "key_risks": [], "recommended_next_steps": []}
    return rep


class _R(dict):
    """Lets repo.put store a plain dict."""
    def model_dump(self, mode="json"):
        import json
        return json.loads(json.dumps(self, default=str))
