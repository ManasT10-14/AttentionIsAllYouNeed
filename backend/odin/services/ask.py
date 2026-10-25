"""Ask Odin — Q&A over the contract portfolio: portfolio facts from structured data, clause claims from verified citations."""
from __future__ import annotations

import re
from datetime import date

from odin.agents.base import j, prompt
from odin.core import citations
from odin.core.config import odin_config
from odin.core.context import run_ctx
from odin.core.models import AskAnswer
from odin.core.telemetry import traced
from odin.db import repo
from odin.evals import scored
from odin.llm.call import structured
from odin.retrieval import hybrid
from odin.services import insights

# Questions about the portfolio as a whole (answerable from structured data, no clause quote required).
_PORTFOLIO = re.compile(
    r"\b(contracts|agreements|portfolio|counterparties|parties|exposure|upcoming|how many|overview|total|"
    r"what do we have|who are|summari[sz]e|(which|what|list)\b.*\b(contract|agreement)s?|renew\w* (next|this|in|by)|"
    r"(expir\w*|deadlines?|alerts?)\b.*\b(next|this|soon|upcoming))\b", re.I)
_GENERIC = {"agreement", "contract", "services", "service", "master", "terms", "the", "and", "of", "for"}
_SKIP_KEYS = {"citation", "confidence", "status", "source", "bboxes"}


def classify(question: str) -> str:
    """portfolio = cheap rule; anything else is a clause question (hybrid RAG, evidence required)."""
    return "portfolio" if _PORTFOLIO.search(question) else "clause"


def _mentioned(question: str, contracts) -> list[str]:
    q = question.lower()
    out = []
    for c in contracts:
        words = {w for w in re.findall(r"[a-z]{4,}", (c.title or "").lower())} - _GENERIC
        if c.contract_id.lower() in q or any(w in q for w in words):
            out.append(c.contract_id)
    return out


def _slim(x):
    if isinstance(x, dict):
        return {k: _slim(v) for k, v in x.items() if k not in _SKIP_KEYS and v not in (None, [], "")}
    if isinstance(x, list):
        return [_slim(v) for v in x]
    return x


def portfolio_context(question: str) -> tuple[dict, list[str]]:
    """Compact portfolio snapshot for the model. Returns (context, mentioned contract ids)."""
    now = repo.sim_now()
    cs = repo.contracts()
    exp = {p["contract_id"]: p for p in insights.exposure_summary(now)["contracts"]}
    rows = []
    for c in cs:
        e = exp.get(c.contract_id, {})
        rows.append({"contract_id": c.contract_id, "title": c.title, "type": c.type, "status": c.status,
                     "parties": [f"{p.get('name')} ({p.get('role')})" for p in c.meta.get("parties", [])],
                     "effective_date": c.meta.get("effective_date"), "governing_law": c.meta.get("governing_law"),
                     "term_end": e.get("term_end"), "notice_deadline": e.get("notice_deadline"),
                     "expected_exposure": e.get("expected"), "worst_case_exposure": e.get("worst_case"),
                     "analysed": c.contract_id in exp})
    ment = _mentioned(question, cs)
    detail = {}
    for cid in ment[:3]:
        x = insights.extraction(cid)
        if x:
            detail[cid] = _slim(x.model_dump(mode="json"))
    ex = insights.exposure_summary(now)
    ctx = {"today": now.isoformat(), "contract_count": len(cs), "contracts": rows,
           "total_exposure": {"expected": ex["expected"], "worst_case": ex["worst_case"], "currency": ex["currency"],
                              "note": ex["note"]},
           "counterparties": [{"name": p["name"], "contracts": p["contracts"], "worst_case": p["worst_case"]}
                              for p in insights.counterparties(now)],
           "open_alerts": [_slim({k: a.get(k) for k in ("contract_id", "title", "severity", "kind", "due_date", "why")})
                           for a in insights.alerts(now)[:15]],
           "extracted_fields_for_mentioned_contracts": detail}
    return ctx, ment


@scored("ask")          # own run id → captured + live-scored like graph runs (odin.evals)
@traced("odin:ask")
def ask(company_id: str, question: str, contract_ids: list[str] | None = None) -> dict:
    with run_ctx(company_id, agent="ask"):
        kind = classify(question)
        ctx, ment = portfolio_context(question)
        ids = contract_ids or ment
        sources = [{"contract_id": r["contract_id"], "title": r["title"]} for r in ctx["contracts"]
                   if r["contract_id"] in ids]
        if not ctx["contract_count"]:
            return {"answer": "No contracts have been uploaded yet. Upload contracts and I can answer questions about them.",
                    "citations": [], "insufficient_evidence": True, "passages": [], "kind": kind, "sources": []}
        scope_ids = ids or None
        queries = [question]
        if kind == "clause" and odin_config()["retrieval"].get("multi_query"):
            from pydantic import BaseModel

            class Q(BaseModel):
                queries: list[str]
            queries += structured("ask", Q, "Rewrite the question into 3 short search queries for contract clauses.",
                                  question).queries[:3]
        seen, hits = set(), []
        for q in queries:
            for h in hybrid.search(q, contract_ids=scope_ids):
                if h.clause_id not in seen:
                    seen.add(h.clause_id)
                    hits.append(h)
        passages = [h.as_dict(1500) for h in hits[:12 if kind == "clause" else 6]]
        if kind == "clause" and not passages:
            return {"answer": "I do not have supporting contract evidence for this question.",
                    "citations": [], "insufficient_evidence": True, "passages": [], "kind": kind, "sources": sources}
        ans = structured("ask", AskAnswer, prompt("ask"),
                         f"Question type: {kind}\nQuestion: {question}\n\n<portfolio>\n{j(ctx)}\n</portfolio>\n\n"
                         f"<document contract_id=\"multiple\">\n{j(passages)}\n</document>",
                         tools=["get_clause", "hybrid_search"])
        ans.citations = citations.verify_all(ans.citations)
        if kind == "clause":
            if not ans.citations or not all(c.verified for c in ans.citations):
                ans.insufficient_evidence = True
                ans.answer = "I could not verify supporting contract evidence for this answer."
        else:   # portfolio answer: structured data is the source; keep only quotes that verified
            ans.citations = [c for c in ans.citations if c.verified]
        return {**ans.model_dump(mode="json"), "passages": passages, "kind": kind, "sources": sources}
