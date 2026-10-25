"""HEIMDALL — event monitoring & verification (FR5)."""
from __future__ import annotations

import hashlib

from odin.agents.base import agent_node, j, prompt, say, tool
from odin.core import citations
from odin.core.config import limits
from odin.core.models import (SEVERITY_RANK, Alert, Citation, EventMapping, HeimdallVerifications, Verification,
                              Violation, new_id)
from odin.db import repo
from odin.llm.call import structured
from odin.services import insights


def _targets(state: dict) -> list[dict]:
    if state.get("debate_round", 0) > 0:
        ids = state.get("disputed") or []
        return [f for f in (repo.get("finding", i) for i in ids) if f and f.get("status") == "open"]
    if state.get("finding_ids") is not None:
        return [f for f in (repo.get("finding", i) for i in state["finding_ids"]) if f and f.get("status") == "open"]
    return repo.query("finding", contract_id=state["contract_id"], status="open")


@agent_node("heimdall")
def verify(state: dict) -> dict:
    findings = _targets(state)
    cid = state.get("contract_id")
    if not findings:
        return {"disputed": []}
    cited = {(c["contract_id"], c["clause_number"]) for f in findings for c in f.get("citations", [])}
    clauses = [tool("get_clause", {"contract_id": a, "clause_number": b}) for a, b in sorted(cited)][:25]
    evs = tool("get_events", {"contract_id": cid if cid not in (None, "cross") else None})
    user = (f"Findings to verify:\n{j([{k: f.get(k) for k in ('id', 'kind', 'claim', 'attack_path', 'severity', 'likelihood', 'citations', 'debate')} for f in findings])}\n\n"
            f"<document contract_id=\"{cid}\">\nCited clauses (exact text):\n{j(clauses)}\n</document>\n\n"
            f"<email>\nEvents so far:\n{j(evs)[:6000]}\n</email>")
    # cited clause text is already in the prompt → no tool round-trips (latency)
    out = structured("heimdall", HeimdallVerifications, prompt("heimdall_verify"), user, meta={"contract_id": cid})
    valid = {f["id"] for f in findings}
    disputed, counts = [], {"support": 0, "challenge": 0, "insufficient": 0}
    for v in out.verifications:
        if v.finding_id not in valid:
            continue
        counts[v.verdict] += 1
        tool("save_verification", {"verification": Verification(id=new_id("vf"), round=state.get("debate_round", 0),
                                                                 **v.model_dump()).model_dump(mode="json")})
        f = repo.get("finding", v.finding_id)
        hist = (f.get("debate") or []) + [{"by": "heimdall", "verdict": v.verdict, "rationale": v.rationale}]
        status = {"support": "verified", "challenge": "challenged", "insufficient": "open"}[v.verdict]
        repo.set_status(v.finding_id, status, debate=hist)
        if v.verdict == "challenge" and f.get("severity", 0) >= limits().get("debate_min_severity", 3):
            disputed.append(v.finding_id)       # low-severity challenges stay "challenged" without a debate round
    say("heimdall", "tyr" if disputed else "loki", "verify",
        f"{cid or 'event'}: supported {counts['support']}, challenged {counts['challenge']}, "
        f"insufficient {counts['insufficient']}.", payload={**counts, "disputed": disputed}, contract_id=cid)
    return {"disputed": disputed}


# ───────────────────────────── events ─────────────────────────────
@agent_node("heimdall")
def map_event(state: dict) -> dict:
    ev = repo.get("event", state["event_id"])
    known = [c["contract_id"] for c in tool("list_contracts", {})]
    named = [c for c in ev.get("contract_ids", []) if c in known]
    query = f"{ev['event_type'].replace('_', ' ').lower()} {ev.get('description', '')} {ev.get('counterparty', '')}"
    hits = tool("hybrid_search", {"query": query[:500], "contract_ids": named or None, "top_k": 10})
    cascade = sorted({d for c in named for d in insights.cascade(c)})
    user = (f"<email>\n{j({k: ev.get(k) for k in ('event_type', 'occurred_at', 'contract_ids', 'counterparty', 'amount', 'reference', 'description')})}\n</email>\n\n"
            f"Known contracts: {known}\nContracts that depend on the named ones (cascade): {cascade}\n"
            f"Simulated today: {repo.sim_now()}\n\n"
            f"<document contract_id=\"{','.join(named) or 'all'}\">\nCandidate clauses:\n{j(hits)}\n</document>")
    m = structured("heimdall", EventMapping, prompt("heimdall_map"), user, tools=["get_clause", "hybrid_search"],
                   meta={"event_id": ev["id"]})
    m.affected_contract_ids = [c for c in m.affected_contract_ids if c in known] or named
    if m.is_noise or not m.affected_contract_ids:
        repo.set_status(ev["id"], "noise", reject_reason=m.noise_reason or "no contract affected")
        say("heimdall", "odin", "event", f"Event {ev['event_type']} filtered as noise: {m.noise_reason}",
            payload={"event_id": ev["id"]})
        return {"noise": True}

    m.affected_clauses = citations.verify_all(m.affected_clauses)
    viol_ids = []
    for vd in m.violations:
        row = repo.clause_by_number(vd.contract_id, vd.clause_number)
        cit = citations.verify(Citation(contract_id=vd.contract_id, clause_number=vd.clause_number, quote=vd.quote))
        if not row or not cit.verified:
            say("heimdall", "odin", "event", f"Discarded unverifiable violation claim on {vd.contract_id} "
                f"§{vd.clause_number} (quote not found in contract).", contract_id=vd.contract_id)
            continue
        row = repo.clause_by_number(vd.contract_id, cit.clause_number)
        v = Violation(id=new_id("vio"), event_id=ev["id"], contract_id=vd.contract_id, version=row.version,
                      clause_id=row.id, clause_number=row.number, quote=vd.quote, page=row.page, bboxes=row.bboxes,
                      breach_type=vd.breach_type, breached_by=vd.breached_by, exposure=vd.exposure,
                      explanation=vd.explanation)
        tool("create_violation", {"violation": v.model_dump(mode="json")})
        viol_ids.append(v.id)

    key = f"event:{ev['id']}"
    alert = Alert(id="al-" + hashlib.sha1(key.encode()).hexdigest()[:12], dedupe_key=key, severity=m.alert_severity,
                  kind="event", title=m.alert_title or f"{ev['event_type']} on {', '.join(m.affected_contract_ids)}",
                  why=m.effect, contract_id=m.affected_contract_ids[0], citations=m.affected_clauses,
                  event_id=ev["id"], violation_id=viol_ids[0] if viol_ids else None)
    tool("create_alert", {"alert": alert.model_dump(mode="json")})
    if SEVERITY_RANK[m.alert_severity] >= SEVERITY_RANK["high"]:
        tool("post_webhook", {"event": "alert", "payload": alert.model_dump(mode="json")})
    for dep in cascade:      # cascade chain alerts (deterministic)
        ck = f"cascade:{ev['id']}:{dep}"
        tool("create_alert", {"alert": Alert(id="al-" + hashlib.sha1(ck.encode()).hexdigest()[:12], dedupe_key=ck,
                                             severity="medium", kind="cascade", contract_id=dep, event_id=ev["id"],
                                             title=f"Knock-on risk: {dep} depends on {', '.join(named)}",
                                             why=f"{ev['event_type']} on {', '.join(named)} may cascade to {dep} "
                                                 f"(dependency recorded by LOKI).").model_dump(mode="json")})
    repo.set_status(ev["id"], "processed", contract_ids=m.affected_contract_ids)
    say("heimdall", "loki", "event",
        f"{ev['event_type']} → {', '.join(m.affected_contract_ids)}: {m.effect[:240]}"
        + (f" {len(viol_ids)} violation(s) recorded." if viol_ids else ""),
        payload={"event_id": ev["id"], "violations": viol_ids, "severity": m.alert_severity},
        contract_id=m.affected_contract_ids[0])
    return {"contract_ids": m.affected_contract_ids, "violation_ids": viol_ids,
            "affected_clauses": [c.model_dump(mode="json") for c in m.affected_clauses],
            "mapping": m.model_dump(mode="json", exclude={"violations"})}
