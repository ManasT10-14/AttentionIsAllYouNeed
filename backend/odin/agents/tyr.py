"""TYR — arbitration & action drafting (FR6)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from odin.agents.base import agent_node, company_ctx, j, override_note, prompt, say, tool
from odin.core.models import clause_ref, ActionDraft, ActionDraftOut, Ruling, TyrActions, TyrRulings, new_id
from odin.db import repo
from odin.llm.call import structured
from odin.services import insights

APPROVAL_ALWAYS = {"termination_notice", "breach_notice", "amendment", "non_renewal_notice", "renewal_notice",
                   "payment_instruction"}


@agent_node("tyr")
def rule(state: dict) -> dict:
    ids = [i for i in (state.get("disputed") or [])]
    findings = [f for f in (repo.get("finding", i) for i in ids) if f and f.get("status") in ("challenged", "open")]
    if not findings:
        return {"disputed": []}
    vers = repo.query("verification")
    user = "Disputes:\n" + j([{"finding": f, "verifications": [v for v in vers if v["finding_id"] == f["id"]]}
                              for f in findings])
    out = structured("tyr", TyrRulings, prompt("tyr_rule"), user, meta={"contract_id": state.get("contract_id")})
    valid = {f["id"]: f for f in findings}
    for r in out.rulings:
        if r.finding_id in valid:
            tool("save_ruling", {"ruling": Ruling(id=new_id("rul"), **r.model_dump()).model_dump(mode="json"),
                                 "contract_id": valid[r.finding_id]["contract_id"]})
            say("tyr", "odin", "rule", f"Ruling on '{valid[r.finding_id]['claim'][:80]}': {r.winner} "
                f"(severity {r.final_severity}, conf {r.confidence:.2f}) — {r.rationale[:200]}",
                payload={"finding_id": r.finding_id, "winner": r.winner}, contract_id=valid[r.finding_id]["contract_id"])
    return {"disputed": []}


def _threshold() -> float | None:
    t = (company_ctx() or {}).get("approval_threshold")
    return t.get("amount") if t else None


def _store_actions(drafts: list[ActionDraftOut], contract_id: str, event_id: str | None = None) -> list[str]:
    thr = _threshold()
    today = repo.sim_now()
    ids = []
    for a in drafts:
        sev = 0
        for fid in a.related_finding_ids:
            f = repo.get("finding", fid)
            sev = max(sev, (f or {}).get("severity", 0))
        days = (a.deadline - today).days if a.deadline else 90
        urgency = 3 if days <= 7 else 2 if days <= 30 else 1 if days <= 90 else 0
        money = (a.est_exposure_avoided.amount if a.est_exposure_avoided else 0)
        needs = (a.kind in APPROVAL_ALWAYS or a.confidence < 0.8
                 or (thr is not None and money >= thr))
        act = ActionDraft(id=new_id("act"), contract_id=contract_id, event_id=event_id, needs_human_approval=needs,
                          priority=round(urgency * 2 + sev + min(money / 100000, 5) + a.confidence, 2),
                          **a.model_dump())
        tool("draft_action", {"action": act.model_dump(mode="json")})
        ids.append(act.id)
    return ids


def _cited_clauses(*groups) -> str:
    """Exact text of every clause the inputs cite, given up front → no tool round-trips (each one re-sent the
    whole ~30k-token context and made Tyr the slowest agent)."""
    keys = sorted({(c["contract_id"], c["clause_number"]) for items in groups for it in items if it
                   for c in (it.get("citations") or ([it["citation"]] if it.get("citation") else []))})
    rows = [tool("get_clause", {"contract_id": a, "clause_number": b}) for a, b in keys[:40]]
    over = {(o.get("doc"), str(o.get("number"))): o for o in insights.clause_overrides()}
    return "<document contract_id=\"cited\">\n" + "\n".join(
        f"[{r['contract_id']} {clause_ref(r['clause_number'])}] {r['text']}"
        + (f"\n{override_note(over[(r['contract_id'], r['clause_number'])])}" if (r['contract_id'], r['clause_number']) in over else "")
        for r in rows if "text" in r) + "\n</document>"


def _slim_findings(fs: list[dict]) -> list[dict]:
    return [{k: f.get(k) for k in ("id", "contract_id", "kind", "claim", "severity", "likelihood", "status",
                                   "other_contract_ids", "who", "why", "consequence", "exposure") if f.get(k)}
            | {"clauses": [f"{c['contract_id']} {c.get('ref') or c['clause_number']}" for c in f.get("citations", [])]}
            for f in fs]


def _notice_addresses(ids: list[str] | None) -> dict:
    out = {}
    for c in repo.contracts():
        x = insights.extraction(c.contract_id) if ids is None or c.contract_id in ids else None
        if x and x.notice and (x.notice.address or x.notice.authorized_sender):
            out[c.contract_id] = {"address": x.notice.address, "sender": x.notice.authorized_sender}
    return out


def _slim_timeline(tl: dict) -> list[dict]:
    return [{"contract_id": t["contract_id"], "term_end": t["term_end"], "notice_deadline": t["notice_deadline"],
             "expected": t["exposure"]["expected"], "worst_case": t["exposure"]["worst_case"],
             "next": [{k: e.get(k) for k in ("date", "kind", "title", "status", "amount")}
                      for e in t["entries"] if e["status"] in ("due", "upcoming", "missed")][:12]}
            for t in tl["contracts"]]


@agent_node("tyr")
def actions(state: dict) -> dict:
    cid = state["contract_id"]
    if state.get("mode") != "update":
        for a in repo.query("action", contract_id=cid, status="draft"):
            if not a.get("event_id"):
                repo.set_status(a["id"], "superseded")
    head, members = insights.family_of(cid) if cid != "cross" else (cid, [cid])
    if head != cid and state.get("mode") != "update":
        return {}            # family members are handled by the family head's workstream
    findings = [f for f in repo.query("finding", contract_id=cid, status=["verified", "ruled", "open"])]
    tl = tool("compute_timeline", {"contract_id": None})
    if cid != "cross":
        tl["contracts"] = [t for t in tl["contracts"] if t["contract_id"] in members]
    viols = [v for m in members for v in repo.query("violation", contract_id=m)] if cid != "cross" else []
    user = (f"Today (simulated): {repo.sim_now()}\nCompany context:\n{j(company_ctx())}\n\n"
            + (f"Document family reviewed together: {'+'.join(members)}\n" if len(members) > 1 else "")
            + f"Counterparty notice addresses: {j(_notice_addresses(members if cid != 'cross' else None))}\n\n"
            f"Findings (status verified/ruled are confirmed; open = unconfirmed):\n{j(_slim_findings(findings))}\n\n"
            f"Timeline & exposure:\n{j(_slim_timeline(tl))}\n\nViolations:\n{j(viols)[:5000]}\n\n"
            f"Cited clause text (quote from here):\n{_cited_clauses(findings, viols)}\n\n"
            "Draft at most 4 actions, each body under 250 words.")
    out = structured("tyr", TyrActions, prompt("tyr_actions"), user, meta={"contract_id": cid})
    ids = _store_actions(out.actions, cid)
    say("tyr", "odin", "action", f"{cid}: {len(ids)} actions drafted "
        f"({sum(1 for a in out.actions if a.kind != 'escalation_memo')} notices/amendments).",
        payload={"action_ids": ids}, contract_id=cid)
    return {}


class ViolationVerdict(BaseModel):
    violation_id: str
    status: Literal["confirmed", "dismissed"]
    rationale: str


class TyrEventOut(BaseModel):
    violation_verdicts: list[ViolationVerdict] = []
    actions: list[ActionDraftOut] = []


@agent_node("tyr")
def decide_event(state: dict) -> dict:
    ev = repo.get("event", state["event_id"])
    viols = [repo.get("violation", v) for v in state.get("violation_ids", [])]
    findings = [repo.get("finding", f) for f in state.get("finding_ids", [])]
    cids = state.get("contract_ids") or []
    tl = tool("compute_timeline", {"contract_id": cids[0] if len(cids) == 1 else None})
    holidays = [{k: h.get(k) for k in ("date", "name", "observed_by")} for h in repo.query("holiday")]
    user = (f"Today (simulated): {repo.sim_now()}\nCompany context:\n{j(company_ctx())}\n\n"
            f"Counterparty notice addresses: {j(_notice_addresses(None))}\n"
            + (f"Observed holidays: {j(holidays)}\n" if holidays else "") + "\n"
            f"<email>\n{j({k: ev.get(k) for k in ('event_type', 'occurred_at', 'sender', 'recipient', 'channel', 'subject', 'amount', 'description')})}\n</email>\n\n"
            f"HEIMDALL's reading: {j(ev.get('effect', ''))}\n\n"
            f"Suspected violations:\n{j(viols)}\n\nRisk findings after debate:\n{j(findings)}\n\n"
            f"Timeline & exposure:\n{j(_slim_timeline(tl))}\n\n"
            f"Cited clause text (quote from here):\n{_cited_clauses(findings, viols)}")
    out = structured("tyr", TyrEventOut, prompt("tyr_event"), user, meta={"event_id": ev["id"]})
    valid = {v["id"] for v in viols if v}
    for vv in out.violation_verdicts:
        if vv.violation_id in valid:
            rid = new_id("rul")
            repo.set_status(vv.violation_id, vv.status, ruling_id=rid, ruling_rationale=vv.rationale)
            say("tyr", "odin", "rule", f"Violation {vv.status}: {vv.rationale[:220]}",
                payload={"violation_id": vv.violation_id}, contract_id=cids[0] if cids else None)
    ids = []
    for a in out.actions:
        a.related_violation_ids = [v for v in a.related_violation_ids if v in valid] or list(valid)
        cid = next((c.contract_id for c in a.citations if c.contract_id in cids), cids[0] if cids else "cross")
        ids += _store_actions([a], cid, event_id=ev["id"])
    say("tyr", "odin", "action", f"Event {ev['event_type']}: {len(ids)} actions drafted.", payload={"action_ids": ids},
        contract_id=cids[0] if cids else None)
    return {}


@agent_node("tyr")
def amend(state: dict) -> dict:
    cid = state["contract_id"]
    changes = state.get("changes") or []
    if not changes:
        return {}
    findings = repo.query("finding", contract_id=cid, status=["open", "verified", "ruled"])
    user = (f"Company context:\n{j(company_ctx())}\n\n<document contract_id=\"{cid}\">\nChanged clauses "
            f"(v{state['from_version']} → v{state['to_version']}):\n{j(changes)[:20000]}\n</document>\n\n"
            f"Open findings:\n{j(_slim_findings(findings))}")
    out = structured("tyr", TyrActions, prompt("tyr_amend"), user, meta={"contract_id": cid})
    out.actions = [a for a in out.actions if a.kind == "amendment" and a.redlines] + \
                  [a for a in out.actions if a.kind != "amendment"]
    ids = _store_actions(out.actions, cid)
    say("tyr", "odin", "action", f"{cid} v{state['to_version']}: {len(ids)} amendment proposals.",
        payload={"action_ids": ids}, contract_id=cid)
    return {}
