"""THOR — extraction (FR2)."""
from __future__ import annotations

import re

from odin.agents.base import agent_node, company_ctx, doc_block, j, pmap, prompt, say, tool
from odin.core.models import (EXTRACTION_LIST_FIELDS, EXTRACTION_ONE_FIELDS, ClauseReextraction,
                               ContractExtraction)
from odin.db import repo
from odin.llm.call import structured
from odin.services import insights

LIST_FIELDS, ONE_FIELDS = EXTRACTION_LIST_FIELDS, EXTRACTION_ONE_FIELDS


def summarize(x: ContractExtraction) -> dict:
    fs = insights._fields(x)
    return {"fields": len(fs), "flags": len(x.flags),
            "verified": sum(1 for f in fs if f.citation and f.citation.verified),
            "low_confidence": sum(1 for f in fs if f.confidence < 0.7),
            "mean_confidence": round(sum(f.confidence for f in fs) / len(fs), 3) if fs else 0.0}


@agent_node("thor")
def extract(state: dict) -> dict:
    cid, ver = state["contract_id"], state["version"]
    if insights.extraction(cid, ver) and not state.get("force"):
        say("thor", "odin", "extract", f"{cid} v{ver}: extraction already in store — reused (no re-read).",
            contract_id=cid)
        return {}
    rows = repo.clauses(cid, ver, current_only=False)
    c = repo.contract(cid)
    rels = [r for r in insights.doc_relations() if cid in (r.get("from_doc"), r.get("to_doc"))]
    user = (f"Company context:\n{j(company_ctx())}\n\nContract cover metadata:\n{j(c.meta)}\n\n"
            + (f"Document relations (recorded at ingest):\n{j(rels)}\n\n" if rels else "")
            + f"Contract text (clauses):\n{doc_block(rows)}")
    x = structured("thor", ContractExtraction, prompt("thor"), user, meta={"contract_id": cid, "version": ver})
    tool("save_extraction", {"contract_id": cid, "version": ver, "extraction": x.model_dump(mode="json")})
    s = summarize(insights.extraction(cid, ver))
    say("thor", "loki", "extract",
        f"{cid} v{ver}: {s['fields']} fields extracted, {s['verified']} citations verified, {s['flags']} ambiguity "
        f"flags, {s['low_confidence']} low-confidence.", payload=s, contract_id=cid)
    return {}


def merge(base: ContractExtraction, upd: ContractExtraction, clause_numbers: set[str]) -> ContractExtraction:
    """Replace only fields citing the given clauses (targeted re-extraction, NFR5)."""
    out = base.model_copy(deep=True)
    for name in ONE_FIELDS:
        new = getattr(upd, name)
        if new is not None and (new.citation is None or new.citation.clause_number in clause_numbers
                                or getattr(out, name) is None or getattr(out, name).citation is None
                                or getattr(out, name).citation.clause_number in clause_numbers):
            setattr(out, name, new)
    for name in LIST_FIELDS:
        new_items = getattr(upd, name)
        if not new_items:
            continue
        kept = [f for f in getattr(out, name) if not (f.citation and f.citation.clause_number in clause_numbers)]
        setattr(out, name, kept + new_items)
    if upd.parties:
        out.parties = upd.parties
    out.flags = [f for f in out.flags if f.clause_number not in clause_numbers] + upd.flags
    return out


@agent_node("thor")
def clarify(state: dict) -> dict:
    cid = state["contract_id"]
    x = insights.extraction(cid)
    pending = [c for c in repo.query("clarification", contract_id=cid, status="open")]
    if not pending or not x:
        return {}
    base = x

    def answer(q):
        # Loki sometimes asks about "4.2 / 4.3" or "§2.1 and 2.2" → fetch each clause
        nums = [n.strip(" §") for n in re.split(r"\s*(?:/|,|&|\band\b|\bvs\.?)\s*", q["clause_number"]) if n.strip(" §")]
        clause = [tool("get_clause", {"contract_id": cid, "clause_number": n}) for n in nums]
        related = [tool("get_clause", {"contract_id": cid, "clause_number": n})
                   for f in base.flags if f.clause_number == q["clause_number"] for n in f.related_clauses][:3]
        user = (f"Question from LOKI about field `{q['field_path']}`: {q['question']}\n\n"
                f"Current extraction (for context):\n{j(base.model_dump(mode='json'))[:6000]}\n\n"
                f"<document contract_id=\"{cid}\">\nClause:\n{j(clause)}\nRelated:\n{j(related)}\n</document>")
        return q, nums, structured("thor", ClauseReextraction, prompt("thor_clarify"), user,
                                   meta={"contract_id": cid, "clarification": q["id"]})

    for q, nums, ans in pmap(answer, pending):      # independent questions → parallel; merge in order
        x = merge(x, ans.updated_fields, set(nums))
        repo.set_status(q["id"], "answered", answer=ans.answer, resolved=ans.resolved)
        say("thor", "loki", "clarify", f"{cid} §{q['clause_number']}: {ans.answer[:300]}",
            payload={"clarification_id": q["id"], "resolved": ans.resolved}, contract_id=cid)
    c = repo.contract(cid)
    tool("save_extraction", {"contract_id": cid, "version": c.current_version, "extraction": x.model_dump(mode="json")})
    return {}
