"""LOKI — adversarial review (FR4): single-contract, cross-contract, event reassessment, rebuttals."""
from __future__ import annotations

from odin.agents.base import agent_node, company_ctx, doc_block, j, prompt, say, tool
from odin.core.config import limits
from odin.core.models import Finding, LokiOutput, LokiRebuttals, new_id
from odin.db import repo
from odin.llm.call import structured
from odin.services import insights

READ_TOOLS = ["get_clause", "hybrid_search", "get_extraction", "list_contracts"]
CONFLICT_TOPICS = ["exclusivity exclusive supplier non-compete", "governing law jurisdiction courts arbitration seat",
                   "service level availability uptime service credits", "limitation of liability cap indemnity",
                   "term expiry renewal notice period", "assignment change of control subcontracting",
                   "confidentiality data protection personal data", "premises lease location office"]


def _extraction_digest(cid: str) -> list[dict]:
    x = insights.extraction(cid)
    if not x:
        return []
    out = []
    for name in ("term", "renewal", "liability_cap", "governing_law", "payments", "penalties", "termination",
                 "obligations", "compliance"):
        v = getattr(x, name)
        for f in (v if isinstance(v, list) else [v] if v else []):
            d = f.model_dump(mode="json", exclude={"source"})
            out.append({"field": name, "status": f.status, "confidence": f.confidence,
                        "clause": f.citation.clause_number if f.citation else None,
                        "value": {k: v2 for k, v2 in d.items() if k not in ("citation", "status", "confidence")}})
    return out + [{"flag": fl.model_dump()} for fl in x.flags]


def _save_findings(out: LokiOutput, contract_id: str, event_id: str | None = None) -> list[str]:
    ids = []
    for f in out.findings:
        cross = bool(f.other_contract_ids) or f.kind == "conflict"
        fd = Finding(id=new_id("fd"), contract_id="cross" if cross and contract_id == "cross" else contract_id,
                     event_id=event_id, **f.model_dump())
        tool("save_finding", {"finding": fd.model_dump(mode="json")})
        ids.append(fd.id)
    for d in out.dependencies:
        tool("save_dependency", d.model_dump(mode="json"))
    return ids


@agent_node("loki")
def attack(state: dict) -> dict:
    cid = state["contract_id"]
    focus = state.get("focus_clauses")
    if not focus:   # fresh analysis supersedes this contract's previous findings
        for f in repo.query("finding", contract_id=cid, status=["open", "verified", "challenged", "ruled"]):
            if not f.get("event_id"):
                repo.set_status(f["id"], "superseded")
    rows = repo.clauses(cid, numbers=focus) if focus else repo.clauses(cid)
    user = (f"Company context:\n{j(company_ctx())}\n\nOther contracts of the company:\n"
            f"{j(tool('list_contracts', {}))}\n\nTHOR's extraction (fields, confidence, status, flags):\n"
            f"{j(_extraction_digest(cid))[:12000]}\n\n"
            + (f"FOCUS: only these clauses changed in a new version: {focus}. Review them (and their interaction "
               f"with the rest of the contract).\n\n" if focus else "")
            + f"Contract under review:\n{doc_block(rows)}")
    out = structured("loki", LokiOutput, prompt("loki"), user, tools=READ_TOOLS, meta={"contract_id": cid})
    ids = _save_findings(out, cid)
    clar = _ask_clarifications(out, cid, state.get("clarify_round", 0))
    say("loki", "heimdall", "attack", f"{cid}: {len(ids)} findings raised"
        + (f", {clar} clarification requests sent to THOR" if clar else "") + ".",
        payload={"finding_ids": ids}, contract_id=cid)
    return {"clarify_round": state.get("clarify_round", 0) + (1 if clar else 0)} if clar else {}


def _ask_clarifications(out: LokiOutput, cid: str, rnd: int) -> int:
    if rnd >= limits()["max_clarify_rounds"]:
        return 0
    n = 0
    for c in out.clarifications[:3]:
        tool("request_clarification", {"contract_id": cid, "clause_number": c.clause_number,
                                       "field_path": c.field_path, "question": c.question, "round": rnd})
        say("loki", "thor", "clarify", f"{cid} §{c.clause_number} ({c.field_path}): {c.question}", contract_id=cid)
        n += 1
    return n


@agent_node("loki")
def revisit(state: dict) -> dict:
    """After THOR answered clarifications: maintain / revise / withdraw affected findings (no full re-read)."""
    cid = state["contract_id"]
    answered = [c for c in repo.query("clarification", contract_id=cid, status="answered")
                if not c.get("revisited")]
    if not answered:
        return {}
    clauses = {c["clause_number"] for c in answered}
    findings = [f for f in repo.query("finding", contract_id=cid, status="open")
                if any(ci["clause_number"] in clauses for ci in f.get("citations", []))]
    for c in answered:
        repo.set_status(c["id"], "answered", revisited=True)
    if not findings:
        return {}
    user = (f"THOR's answers:\n{j([{k: c.get(k) for k in ('clause_number', 'field_path', 'question', 'answer', 'resolved')} for c in answered])}"
            f"\n\nYour findings that rely on those clauses:\n{j(findings)}")
    out = structured("loki", LokiRebuttals, prompt("loki_rebut"), user, meta={"contract_id": cid})
    _apply_rebuttals(out, {f["id"] for f in findings})
    say("loki", "heimdall", "rebut", f"{cid}: revisited {len(findings)} findings after THOR's clarifications.",
        contract_id=cid)
    return {}


def _apply_rebuttals(out: LokiRebuttals, allowed: set[str]) -> dict:
    counts = {"maintain": 0, "revise": 0, "withdraw": 0}
    for r in out.rebuttals:
        if r.finding_id not in allowed:
            continue
        counts[r.position] += 1
        f = repo.get("finding", r.finding_id)
        hist = (f.get("debate") or []) + [{"by": "loki", "position": r.position, "argument": r.argument}]
        if r.position == "withdraw":
            repo.set_status(r.finding_id, "withdrawn", debate=hist)
        else:
            upd = {"debate": hist}
            if r.revised_severity:
                upd["severity"] = r.revised_severity
            repo.set_status(r.finding_id, "open", **upd)
    return counts


@agent_node("loki")
def rebut(state: dict) -> dict:
    """Answer HEIMDALL's challenges (debate loop, FR7.1)."""
    ids = state.get("disputed") or []
    if not ids:
        return {}
    findings = [repo.get("finding", i) for i in ids]
    vers = {i: [v for v in repo.query("verification") if v["finding_id"] == i][-1:] for i in ids}
    user = "Challenged findings with HEIMDALL's verification:\n" + j(
        [{"finding": f, "heimdall": vers.get(f["id"])} for f in findings if f])
    out = structured("loki", LokiRebuttals, prompt("loki_rebut"), user, meta={"contract_id": state.get("contract_id")})
    counts = _apply_rebuttals(out, set(ids))
    say("loki", "heimdall", "rebut", f"Debate round {state.get('debate_round', 0)}: maintained {counts['maintain']}, "
        f"revised {counts['revise']}, withdrew {counts['withdraw']}.", payload=counts, contract_id=state.get("contract_id"))
    return {"debate_round": state.get("debate_round", 0) + 1}


@agent_node("loki")
def cross(state: dict) -> dict:
    """Cross-contract workstream (FR4.2)."""
    contracts = tool("list_contracts", {})
    if len(contracts) < 2:
        say("loki", "odin", "attack", "Only one contract — no cross-contract conflicts possible.", contract_id="cross")
        return {}
    for f in repo.query("finding", contract_id="cross", status=["open", "verified", "challenged", "ruled"]):
        if not f.get("event_id"):
            repo.set_status(f["id"], "superseded")
    digests = {c["contract_id"]: {"meta": c, "extraction": _extraction_digest(c["contract_id"])[:40]}
               for c in contracts}
    passages = []
    for topic in CONFLICT_TOPICS:
        hits = tool("hybrid_search", {"query": topic, "top_k": 6})
        if len({h["contract_id"] for h in hits}) > 1:
            passages.append({"topic": topic, "clauses": [{k: h[k] for k in ("contract_id", "clause_number", "text")}
                                                          for h in hits]})
    user = (f"Company context:\n{j(company_ctx())}\n\nContracts:\n{j(digests)[:30000]}\n\n"
            f"<document contract_id=\"multiple\">\nClauses retrieved per conflict topic:\n{j(passages)[:30000]}\n</document>")
    out = structured("loki", LokiOutput, prompt("loki_cross"), user, tools=READ_TOOLS, meta={"contract_id": "cross"})
    for f in out.findings:
        f.kind = "conflict" if f.other_contract_ids else f.kind
    ids = _save_findings(out, "cross")
    say("loki", "heimdall", "attack", f"Cross-contract: {len(ids)} conflicts, {len(out.dependencies)} dependencies.",
        payload={"finding_ids": ids}, contract_id="cross")
    return {}


@agent_node("loki")
def reassess_event(state: dict) -> dict:
    ev = repo.get("event", state["event_id"])
    cids = state.get("contract_ids") or []
    if not cids:
        return {}
    clauses = [tool("get_clause", {"contract_id": c["contract_id"], "clause_number": c["clause_number"]})
               for c in state.get("affected_clauses", [])][:12]
    user = (f"<email>\n{j({k: ev.get(k) for k in ('event_type', 'occurred_at', 'contract_ids', 'amount', 'description', 'counterparty')})}\n</email>\n\n"
            f"HEIMDALL's mapping:\n{j(state.get('mapping', {}))}\n\n"
            f"<document contract_id=\"{','.join(cids)}\">\n{j(clauses)}\n</document>")
    out = structured("loki", LokiOutput, prompt("loki_event"), user, tools=["get_clause", "hybrid_search"],
                     meta={"event_id": state["event_id"]})
    out.clarifications = []
    ids = []
    for f in out.findings:
        cid = next((c.contract_id for c in f.citations if c.contract_id in cids), cids[0])
        fd = Finding(id=new_id("fd"), contract_id=cid, event_id=state["event_id"], **f.model_dump())
        tool("save_finding", {"finding": fd.model_dump(mode="json")})
        ids.append(fd.id)
    say("loki", "heimdall", "attack", f"Event {ev.get('event_type')}: {len(ids)} new risk claims.",
        payload={"finding_ids": ids, "event_id": state["event_id"]}, contract_id=cids[0])
    return {"finding_ids": ids}
