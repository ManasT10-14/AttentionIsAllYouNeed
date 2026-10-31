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
from odin.services.timeline import ContractInputs, ContractTimeline, compute, counterfactual, fmt_date


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


def inputs(contract_id: str, now: date | None = None) -> ContractInputs | None:
    c = repo.contract(contract_id)
    x = extraction(contract_id)
    if not c or not x:
        return None
    # Retain uncertain source data in extraction, but never turn rejected evidence
    # into a dated financial commitment.
    x = x.model_copy(deep=True)
    for field in ("payments", "obligations", "penalties", "milestones"):
        setattr(x, field, [item for item in getattr(x, field) if item.status != "unverified"])
    # A restatement of an existing fee in an amendment is not another payable.
    amended_ids = {r.get("to_doc") for r in doc_relations() if r.get("from_doc") == contract_id and r.get("relation") == "amends"}
    if amended_ids and x.payments:
        signatures = {(p.amount.amount, p.amount.currency, p.frequency)
                      for target in amended_ids for parent in [extraction(target)] if parent
                      for p in parent.payments if p.amount}
        x = x.model_copy(deep=True)
        x.payments = [p for p in x.payments if not p.amount or (p.amount.amount, p.amount.currency, p.frequency) not in signatures]
    now = now or repo.sim_now()
    visible_events = [e for e in events_for(contract_id) if e.occurred_at.date() <= now]
    visible_ids = {e.id for e in visible_events}
    ctx = (repo.company(_cid()).context or {})
    viols = [Violation.model_validate(v) for v in repo.query("violation", contract_id=contract_id)
             if v.get("status") != "superseded" and v.get("event_id") in visible_ids]
    acts = [a for a in repo.query("action", contract_id=contract_id, status=["approved", "sent", "applied"])]
    eff = c.meta.get("effective_date")
    names = [p["name"] for p in c.meta.get("parties", []) if p.get("role") == "company"] + \
            [p.name for p in x.parties if p.role == "company"] + [ctx.get("name", "")]
    return ContractInputs(contract_id=contract_id, extraction=x,
                          effective_date=date.fromisoformat(eff) if eff else None,
                          governing_law=c.meta.get("governing_law", ""), events=visible_events,
                          violations=viols, actions=acts, currency=ctx.get("base_currency", "INR"), owners=owners(),
                          company_names=[n for n in names if n], holidays=repo.query("holiday"),
                          ledger=[r for r in repo.query("ledger") if r.get("contract_id") == contract_id and r["date"] <= now.isoformat()])


def timelines(now: date | None = None) -> list[ContractTimeline]:
    now = now or repo.sim_now()
    out = []
    for c in repo.contracts():
        ci = inputs(c.contract_id, now)
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
            if e.scenario != "baseline" or e.kind not in ("notice_deadline", "payment", "renewal", "expiry", "obligation", "penalty_trigger"):
                continue
            days = (e.date - now).days
            if e.status == "missed":
                sev, why = "critical", f"{e.title} was missed on {fmt_date(e.date)}."
            elif e.status in ("done", "past"):
                continue
            elif days > horizon:
                continue
            else:
                sev = "critical" if days <= 7 else "high" if days <= 14 else "medium" if days <= 30 else "low"
                if e.kind == "payment":
                    sev = "medium" if days <= 7 else "low"
                why = f"{e.kind.replace('_', ' ')} in {days} days ({fmt_date(e.date)})."
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
    prof: dict = defaultdict(lambda: {"contracts": [], "worst_case": 0.0, "violations": 0, "late_payment_events": 0, "worst_case_by_currency": {}})
    for c in repo.contracts():
        for p in c.meta.get("parties", []):
            if p.get("role") == "company":
                continue
            d = prof[p["name"]]
            d["contracts"].append(c.contract_id)
            exposure = exp.get(c.contract_id, {})
            d["worst_case"] += exposure.get("worst_case", 0)
            currency = exposure.get("currency")
            if currency:
                d["worst_case_by_currency"][currency] = d["worst_case_by_currency"].get(currency, 0) + exposure.get("worst_case", 0)
            d["currency"] = next(iter(d["worst_case_by_currency"])) if len(d["worst_case_by_currency"]) == 1 else None
            d["violations"] += len(repo.query("violation", contract_id=c.contract_id))
            d["late_payment_events"] += sum(1 for e in events_for(c.contract_id)
                                            if e.event_type in ("PAYMENT_LATE", "PAYMENT_MISSED"))
    return [{"name": k, **v} for k, v in sorted(prof.items(), key=lambda kv: -kv[1]["worst_case"])]


# ───────────────────────────── graph (FR9.1) ─────────────────────────────
def _conflict_references(edge: dict) -> list[dict]:
    """Resolve source passages for a saved conflict without changing graph topology."""
    import re
    from collections import Counter
    from odin.core.citations import verify
    from odin.core.models import Citation
    from odin.retrieval.hybrid import tokenize

    ids = [edge[key].removeprefix('c:') for key in ('source', 'target')]
    rows = {cid: repo.clauses(cid) for cid in ids}
    refs = []
    for raw in edge.get('citations', []):
        try:
            citation = verify(Citation.model_validate(raw))
            if citation.verified and citation.contract_id in ids:
                refs.append(citation.model_dump(mode='json'))
        except (ValueError, TypeError):
            continue
    reason = edge.get('reason', '')
    def add(row, basis):
        refs.append({'contract_id': row.contract_id, 'clause_number': row.number,
                     'ref': row.ref, 'page': row.page, 'version': row.version,
                     'quote': row.text, 'verified': True, 'reference_basis': basis})
    for cid in ids:
        if any(c['contract_id'] == cid for c in refs):
            continue
        explicit = re.findall(rf'\b{re.escape(cid)}\s*(?:§|sections?|clauses?)\s*([\w.-]+)', reason, re.I)
        for row in rows[cid]:
            if row.number in explicit:
                add(row, 'explicit_reference')
    # Older dependency records contain only a reason. Retrieve the related source
    # on the other side; this locates evidence, not proof of the legal conflict.
    query = set(tokenize(reason + ' ' + ' '.join(c['quote'] for c in refs)))
    for cid in ids:
        if any(c['contract_id'] == cid for c in refs) or not rows[cid]:
            continue
        terms = [(row, set(tokenize(row.heading + ' ' + row.text))) for row in rows[cid]]
        frequency = Counter(word for _, words in terms for word in words)
        row, words = max(terms, key=lambda item: sum(1 / frequency[w] for w in query & item[1]))
        if len(query & words) >= 2:
            add(row, 'related_source')
    return refs


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
    for r in doc_relations():       # incorporates / amends / addendum_to recorded at ingest
        edges.append({"source": f"c:{r['from_doc']}", "target": f"c:{r['to_doc']}", "kind": r["relation"],
                      "reason": r.get("detail", ""), "citations": [r["citation"]] if r.get("citation") else []})
    for f in repo.query("finding", contract_id="cross"):
        if f.get("status") in ("withdrawn", "superseded"):
            continue
        cids = {c["contract_id"] for c in f.get("citations", [])} | set(f.get("other_contract_ids", []))
        cids = sorted(cids)
        for a, b in zip(cids, cids[1:]):
            edges.append({"source": f"c:{a}", "target": f"c:{b}", "kind": "conflicts_with", "reason": f["claim"],
                          "severity": f["severity"], "finding_id": f["id"],
                          "citations": [c for c in f.get("citations", []) if c.get("contract_id") in (a, b)]})
    ids = {n["id"] for n in nodes}  # drop links to contracts referenced in text but never uploaded
    edges = [e for e in edges if e["source"] in ids and e["target"] in ids]
    for edge in edges:
        if edge['kind'] == 'conflicts_with':
            edge['citations'] = _conflict_references(edge)
    known = {c.contract_id for c in repo.contracts()}
    cascades = {c: [x for x in cascade(c) if x in known] for c in known}
    return {"nodes": nodes, "edges": edges, "cascades": {k: v for k, v in cascades.items() if v}}


# ───────────────────────────── document families (cover page + SLA + amendment + addendum) ─────────────────────────────
FAMILY_RELATIONS = ("incorporates", "amends", "addendum_to")


def doc_relations() -> list[dict]:
    return [r for r in repo.query("doc_relation") if r.get("status") != "superseded"]


def clause_overrides(doc: str | None = None) -> list[dict]:
    return sorted([o for o in repo.query("clause_override")
                   if (not doc or o.get("doc") == doc) and o.get("status") != "superseded"
                   and (not o.get("effective") or o["effective"] <= repo.sim_now().isoformat())],
                  key=lambda o: o.get("effective") or "")


def shared_terms(rels: list[dict] | None = None) -> set[str]:
    """Documents incorporated by two or more others (e.g. STD): shared terms, reviewed once, never a family glue."""
    rels = doc_relations() if rels is None else rels
    n = defaultdict(set)
    for r in rels:
        if r.get("relation") == "incorporates":
            n[r["to_doc"]].add(r["from_doc"])
    return {d for d, srcs in n.items() if len(srcs) >= 2}


def families(rels: list[dict] | None = None) -> dict[str, list[str]]:
    """head -> members (head first). A1+A2+A3 is one family (A1 incorporates A2, A3 amends A2/A1); B1+B2 another.
    The head is the member nothing else in the family modifies or is incorporated into."""
    rels = doc_relations() if rels is None else rels
    shared = shared_terms(rels)
    parent: dict[str, str] = {}

    def root(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x
    for r in rels:
        a, b = r.get("from_doc"), r.get("to_doc")
        if a and b and r.get("relation") in FAMILY_RELATIONS and not {a, b} & shared:
            parent[root(a)] = root(b)
    groups = defaultdict(set)
    for d in list(parent):
        groups[root(d)].add(d)
    out = {}
    for members in groups.values():
        not_head = {r["to_doc"] for r in rels if r.get("relation") == "incorporates"} | \
                   {r["from_doc"] for r in rels if r.get("relation") in ("amends", "addendum_to")}
        head = min(members - not_head or members)
        out[head] = [head] + sorted(members - {head})
    return out


def family_of(contract_id: str) -> tuple[str, list[str]]:
    """(head, members) of the contract's family; a standalone contract is its own one-member family."""
    for head, members in families().items():
        if contract_id in members:
            return head, members
    return contract_id, [contract_id]


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
            if e.scenario == "baseline" and e.kind in ("notice_deadline", "payment", "renewal", "expiry", "obligation") and e.status not in ("past", "done"):
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
