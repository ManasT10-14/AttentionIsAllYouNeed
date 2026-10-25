"""Read-side views computed from the shared store at a given simulated time:
timeline, exposure, heatmap, alerts (deadline + event), health score, graph, calibration, ICS, CSV."""
from __future__ import annotations

import csv
import hashlib
import io
from collections import defaultdict
from datetime import date, datetime, timedelta

from odin.core.config import odin_config
from odin.core.models import (EXTRACTION_LIST_FIELDS, EXTRACTION_ONE_FIELDS, SEVERITY_RANK, Alert,
                               ContractExtraction, Event, Violation)
from odin.db import repo
from odin.services.timeline import ContractInputs, ContractTimeline, compute, counterfactual


# ───────────────────────────── loading ─────────────────────────────
def extraction(contract_id: str, version: int | None = None) -> ContractExtraction | None:
    c = repo.contract(contract_id)
    if not c:
        return None
    v = version or c.current_version
    d = repo.get("extraction", f"ext:{contract_id}:v{v}")
    return ContractExtraction.model_validate(d) if d else None


def events_for(contract_id: str | None = None) -> list[Event]:
    evs = [Event.model_validate(e) for e in repo.query("event", status=["processed"])]
    return [e for e in evs if not contract_id or contract_id in e.contract_ids]


def owners() -> dict:
    d = repo.get("owners", f"owners:{_cid()}")
    return (d or {}).get("map", {})


def _cid() -> str:
    from odin.core.context import current
    return current().company_id


def inputs(contract_id: str) -> ContractInputs | None:
    c = repo.contract(contract_id)
    x = extraction(contract_id)
    if not c or not x:
        return None
    ctx = (repo.company(_cid()).context or {})
    viols = [Violation.model_validate(v) for v in repo.query("violation", contract_id=contract_id)
             if v.get("status") != "superseded"]
    acts = [a for a in repo.query("action", contract_id=contract_id, status=["approved", "sent", "applied"])]
    eff = c.meta.get("effective_date")
    names = [p["name"] for p in c.meta.get("parties", []) if p.get("role") == "company"] + \
            [p.name for p in x.parties if p.role == "company"] + [ctx.get("name", "")]
    return ContractInputs(contract_id=contract_id, extraction=x,
                          effective_date=date.fromisoformat(eff) if eff else None,
                          governing_law=c.meta.get("governing_law", ""), events=events_for(contract_id),
                          violations=viols, actions=acts, currency=ctx.get("base_currency", "INR"), owners=owners(),
                          company_names=[n for n in names if n])


def timelines(now: date | None = None) -> list[ContractTimeline]:
    now = now or repo.sim_now()
    out = []
    for c in repo.contracts():
        ci = inputs(c.contract_id)
        if ci:
            out.append(compute(ci, now))
    return out


# ───────────────────────────── exposure / heatmap ─────────────────────────────
def exposure_summary(now: date | None = None) -> dict:
    now = now or repo.sim_now()
    tls = timelines(now)
    per = [{"contract_id": t.contract_id, "expected": t.exposure.expected, "worst_case": t.exposure.worst_case,
            "currency": t.exposure.currency, "term_end": t.term_end, "notice_deadline": t.notice_deadline,
            "assumptions": t.exposure.assumptions} for t in tls]
    return {"as_of": now, "expected": round(sum(p["expected"] for p in per), 2),
            "worst_case": round(sum(p["worst_case"] for p in per), 2),
            "currency": per[0]["currency"] if per else "INR", "contracts": per,
            "note": "Single-currency sum; FX conversion not applied."}


def heatmap(now: date | None = None) -> dict:
    now = now or repo.sim_now()
    cells: dict = defaultdict(float)
    for t in timelines(now):
        for l in t.exposure.lines:
            cells[(t.contract_id, l.clause_type, l.month or now.strftime("%Y-%m"))] += l.amount.amount
    return {"as_of": now, "cells": [{"contract_id": k[0], "clause_type": k[1], "month": k[2], "amount": round(v, 2)}
                                    for k, v in sorted(cells.items())]}


# ───────────────────────────── alerts ─────────────────────────────
def _alert_id(key: str) -> str:
    return "al-" + hashlib.sha1(key.encode()).hexdigest()[:12]


def deadline_alerts(now: date) -> list[Alert]:
    horizon = odin_config()["alerts"]["horizon_days"]
    out = []
    for t in timelines(now):
        for e in t.entries:
            if e.kind not in ("notice_deadline", "payment", "renewal", "expiry", "obligation", "penalty_trigger"):
                continue
            days = (e.date - now).days
            if e.status == "missed":
                sev, why = "critical", f"{e.title} was missed on {e.date}."
            elif e.status in ("done", "past"):
                continue
            elif days > horizon:
                continue
            else:
                sev = "critical" if days <= 7 else "high" if days <= 14 else "medium" if days <= 30 else "low"
                if e.kind == "payment":
                    sev = "medium" if days <= 7 else "low"
                why = f"{e.kind.replace('_', ' ')} in {days} days ({e.date})."
            key = f"{e.contract_id}:{e.kind}:{e.date}"
            out.append(Alert(id=_alert_id(key), dedupe_key=key, severity=sev, kind=e.kind, title=e.title,
                             why=why + (f" Amount {e.amount.currency} {e.amount.amount:,.0f}." if e.amount else ""),
                             contract_id=e.contract_id, due_date=e.date, citations=[e.citation] if e.citation else [],
                             created_at=datetime.combine(now, datetime.min.time())))
    return out


def alerts(now: date | None = None, include_closed: bool = False) -> list[dict]:
    now = now or repo.sim_now()
    stored = {a["dedupe_key"]: a for a in repo.query("alert")}
    merged: dict[str, dict] = {}
    for a in deadline_alerts(now):
        d = a.model_dump(mode="json")
        if a.dedupe_key in stored:          # keep lifecycle state the user set
            s = stored[a.dedupe_key]
            d.update(status=s.get("status", "open"), snooze_until=s.get("snooze_until"))
        merged[a.dedupe_key] = d
    for k, s in stored.items():
        merged.setdefault(k, s)
    min_rank = SEVERITY_RANK[odin_config()["alerts"]["min_severity"]]
    out = []
    for a in merged.values():
        if SEVERITY_RANK.get(a["severity"], 0) < min_rank:
            continue
        if a.get("status") == "snoozed" and a.get("snooze_until") and a["snooze_until"] > now.isoformat():
            if not include_closed:
                continue
        if a.get("status") == "resolved" and not include_closed:
            continue
        out.append(a)
    out.sort(key=lambda a: (-SEVERITY_RANK.get(a["severity"], 0), a.get("due_date") or "9999"))
    return out


# ───────────────────────────── health / calibration / counterparty ─────────────────────────────
def _fields(x: ContractExtraction) -> list:
    out = [getattr(x, n) for n in EXTRACTION_ONE_FIELDS if getattr(x, n)]
    return out + [f for n in EXTRACTION_LIST_FIELDS for f in getattr(x, n)]


def health(contract_id: str, now: date | None = None) -> dict:
    now = now or repo.sim_now()
    x = extraction(contract_id)
    if not x:
        return {"contract_id": contract_id, "score": None, "reason": "not analysed yet"}
    fs = _fields(x)
    if not fs:
        return {"contract_id": contract_id, "score": None, "reason": "no fields extracted"}
    unverified = sum(1 for f in fs if not (f.citation and f.citation.verified))
    findings = [f for f in repo.query("finding", contract_id=contract_id) if f.get("status") not in ("withdrawn", "superseded")]
    viols = [v for v in repo.query("violation", contract_id=contract_id) if v.get("status") == "confirmed"]
    ci = inputs(contract_id)
    missed = sum(1 for e in compute(ci, now).entries if e.status == "missed") if ci else 0
    parts = {"ambiguity_flags": -4 * len(x.flags),
             "unverified_fields": -round(25 * unverified / max(1, len(fs))),
             "open_findings": -min(30, sum(f.get("severity", 1) for f in findings)),
             "confirmed_violations": -10 * len(viols),
             "missed_deadlines": -10 * missed}
    return {"contract_id": contract_id, "score": max(0, 100 + sum(parts.values())), "breakdown": parts}


def calibration() -> dict:
    buckets = defaultdict(lambda: {"n": 0, "verified": 0})
    for c in repo.contracts():
        x = extraction(c.contract_id)
        if not x:
            continue
        for f in _fields(x):
            b = min(9, int(f.confidence * 10))
            buckets[b]["n"] += 1
            buckets[b]["verified"] += int(bool(f.citation and f.citation.verified))
    return {"buckets": [{"confidence": f"{b/10:.1f}-{(b+1)/10:.1f}", "n": v["n"],
                         "verified_rate": round(v["verified"] / v["n"], 3) if v["n"] else None}
                        for b, v in sorted(buckets.items())]}


def counterparties(now: date | None = None) -> list[dict]:
    now = now or repo.sim_now()
    exp = {p["contract_id"]: p for p in exposure_summary(now)["contracts"]}
    prof: dict = defaultdict(lambda: {"contracts": [], "worst_case": 0.0, "violations": 0, "late_payment_events": 0})
    for c in repo.contracts():
        for p in c.meta.get("parties", []):
            if p.get("role") == "company":
                continue
            d = prof[p["name"]]
            d["contracts"].append(c.contract_id)
            d["worst_case"] += exp.get(c.contract_id, {}).get("worst_case", 0)
            d["violations"] += len(repo.query("violation", contract_id=c.contract_id))
            d["late_payment_events"] += sum(1 for e in events_for(c.contract_id)
                                            if e.event_type in ("PAYMENT_LATE", "PAYMENT_MISSED"))
    return [{"name": k, **v} for k, v in sorted(prof.items(), key=lambda kv: -kv[1]["worst_case"])]


# ───────────────────────────── graph (FR9.1) ─────────────────────────────
def graph() -> dict:
    nodes, edges = [], []
    party_ids: dict[str, str] = {}
    for c in repo.contracts():
        nodes.append({"id": f"c:{c.contract_id}", "type": "contract", "label": c.title or c.contract_id,
                      "contract_id": c.contract_id, "contract_type": c.type, "version": c.current_version})
        for p in c.meta.get("parties", []):
            pid = party_ids.setdefault(p["name"], f"p:{len(party_ids)}")
            if not any(n["id"] == pid for n in nodes):
                nodes.append({"id": pid, "type": "party", "label": p["name"], "role": p.get("role")})
            edges.append({"source": pid, "target": f"c:{c.contract_id}", "kind": "party_to"})
        hot = {f["citations"][0]["clause_number"] for f in repo.query("finding", contract_id=c.contract_id)
               if f.get("citations") and f.get("status") not in ("withdrawn", "superseded")}
        hot |= {v["clause_number"] for v in repo.query("violation", contract_id=c.contract_id)}
        for cl in repo.clauses(c.contract_id):
            if cl.number in hot:
                nid = f"cl:{c.contract_id}:{cl.number}"
                nodes.append({"id": nid, "type": "clause", "label": f"{cl.number} {cl.heading}".strip()[:40],
                              "contract_id": c.contract_id, "clause_number": cl.number, "clause_type": cl.clause_type})
                edges.append({"source": f"c:{c.contract_id}", "target": nid, "kind": "contains"})
    for d in repo.query("dependency"):
        if d.get("status") == "superseded":
            continue
        edges.append({"source": f"c:{d['from_contract']}", "target": f"c:{d['to_contract']}", "kind": d["kind"],
                      "reason": d.get("reason", ""), "citations": d.get("citations", [])})
    for f in repo.query("finding", contract_id="cross"):
        if f.get("status") in ("withdrawn", "superseded"):
            continue
        cids = {c["contract_id"] for c in f.get("citations", [])} | set(f.get("other_contract_ids", []))
        cids = sorted(cids)
        for a, b in zip(cids, cids[1:]):
            edges.append({"source": f"c:{a}", "target": f"c:{b}", "kind": "conflicts_with", "reason": f["claim"],
                          "severity": f["severity"], "finding_id": f["id"]})
    ids = {n["id"] for n in nodes}  # drop links to contracts referenced in text but never uploaded
    edges = [e for e in edges if e["source"] in ids and e["target"] in ids]
    known = {c.contract_id for c in repo.contracts()}
    cascades = {c: [x for x in cascade(c) if x in known] for c in known}
    return {"nodes": nodes, "edges": edges, "cascades": {k: v for k, v in cascades.items() if v}}


def cascade(contract_id: str) -> list[str]:
    """Contracts reachable from `contract_id` via depends_on edges (feature: cascade chains)."""
    deps = defaultdict(set)
    for d in repo.query("dependency"):
        if d.get("kind") == "depends_on" and d.get("status") != "superseded":
            deps[d["to_contract"]].add(d["from_contract"])     # from depends on to → to's failure hits from
    seen, stack = [], [contract_id]
    while stack:
        cur = stack.pop()
        for nxt in deps.get(cur, ()):
            if nxt not in seen and nxt != contract_id:
                seen.append(nxt)
                stack.append(nxt)
    return seen


# ───────────────────────────── exports ─────────────────────────────
def ics(now: date | None = None) -> str:
    now = now or repo.sim_now()
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RAGNAROK//Odin//EN"]
    for t in timelines(now):
        for e in t.entries:
            if e.kind in ("notice_deadline", "payment", "renewal", "expiry", "obligation") and e.status not in ("past", "done"):
                out += ["BEGIN:VEVENT", f"UID:{e.id}@odin", f"DTSTART;VALUE=DATE:{e.date.strftime('%Y%m%d')}",
                        f"DTEND;VALUE=DATE:{(e.date + timedelta(days=1)).strftime('%Y%m%d')}",
                        f"SUMMARY:[{e.contract_id}] {e.title}"[:250],
                        f"DESCRIPTION:Clause {e.citation.clause_number if e.citation else '-'}", "END:VEVENT"]
    out.append("END:VCALENDAR")
    return "\r\n".join(out)


def actions_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["priority", "id", "contract_id", "kind", "subject", "deadline", "confidence", "status",
                "needs_approval", "clauses"])
    for a in prioritized_actions():
        w.writerow([a.get("priority"), a["id"], a["contract_id"], a["kind"], a["subject"], a.get("deadline"),
                    a["confidence"], a["status"], a["needs_human_approval"],
                    "; ".join(f"{c['contract_id']} {c['clause_number']}" for c in a.get("citations", []))])
    return buf.getvalue()


def prioritized_actions() -> list[dict]:
    acts = [a for a in repo.query("action") if a.get("status") not in ("superseded", "rejected")]
    return sorted(acts, key=lambda a: -(a.get("priority") or 0))


def action_value(action: dict, now: date | None = None) -> dict:
    ci = inputs(action["contract_id"]) if action.get("contract_id") not in (None, "cross") else None
    if not ci:
        return {}
    return counterfactual(ci, now or repo.sim_now(), action["kind"])
