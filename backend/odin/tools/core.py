"""Every capability an agent has, as a registered tool. Agents get explicit allowlists at the bottom."""
from __future__ import annotations

import json
from datetime import date
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from odin.core import citations
from odin.core.config import settings
from odin.core.context import current
from odin.core.hooks import HOOKS
from odin.core.models import (ActionDraft, Alert, ContractExtraction, Finding, Ruling, Verification, Violation,
                              new_id)
from odin.db import repo
from odin.retrieval import hybrid
from odin.services import insights
from odin.tools.registry import REGISTRY


# ───────────────────────────── arg models ─────────────────────────────
class NoArgs(BaseModel):
    pass


class GetClauseArgs(BaseModel):
    contract_id: str
    clause_number: str
    version: Optional[int] = None


class SearchArgs(BaseModel):
    query: str = Field(description="Natural-language or keyword query, e.g. 'auto renewal notice period'")
    contract_ids: Optional[list[str]] = Field(None, description="Restrict to these CONTRACT IDs")
    clause_types: Optional[list[str]] = Field(None, description="e.g. ['payment','penalty','termination']")
    top_k: int = 8


class ContractArgs(BaseModel):
    contract_id: str


class OptContractArgs(BaseModel):
    contract_id: Optional[str] = None


class TimelineArgs(BaseModel):
    contract_id: Optional[str] = None
    as_of: Optional[date] = None


class SaveExtractionArgs(BaseModel):
    contract_id: str
    version: int
    extraction: ContractExtraction


class ClarifyArgs(BaseModel):
    contract_id: str
    clause_number: str
    field_path: str
    question: str
    round: int = 0


class FindingArgs(BaseModel):
    finding: Finding


class VerificationArgs(BaseModel):
    verification: Verification


class RulingArgs(BaseModel):
    ruling: Ruling
    contract_id: str


class ActionArgs(BaseModel):
    action: ActionDraft


class AlertArgs(BaseModel):
    alert: Alert


class ViolationArgs(BaseModel):
    violation: Violation


class DependencyArgs(BaseModel):
    from_contract: str
    to_contract: str
    kind: str
    reason: str
    citations: list = []


class GmailArgs(BaseModel):
    to: str
    subject: str
    body: str
    thread_id: Optional[str] = None


class AmendArgs(BaseModel):
    action_id: str


class WebhookArgs(BaseModel):
    event: str
    payload: dict


# ───────────────────────────── read tools ─────────────────────────────
@REGISTRY.tool(args=GetClauseArgs, scope="read_contract")
def get_clause(a: GetClauseArgs) -> dict:
    """Exact text of one clause by contract id + clause number (no retrieval)."""
    r = repo.clause_by_number(a.contract_id, a.clause_number, a.version)
    if not r:
        return {"error": f"clause {a.clause_number} not found in {a.contract_id}"}
    HOOKS.record("document", current().agent, None,
                 {"contract_id": r.contract_id, "version": r.version, "clause_number": r.number,
                  "company_id": r.company_id, "text": r.text}, {})
    return {"contract_id": r.contract_id, "version": r.version, "clause_number": r.number, "heading": r.heading,
            "page": r.page, "clause_type": r.clause_type, "text": r.text}


@REGISTRY.tool(args=SearchArgs, scope="retrieval")
def hybrid_search(a: SearchArgs) -> list[dict]:
    """Hybrid (BM25 + dense) search over current clauses of the company's contracts."""
    return [h.as_dict() for h in hybrid.search(a.query, contract_ids=a.contract_ids, clause_types=a.clause_types,
                                               top_k=a.top_k)]


@REGISTRY.tool(args=NoArgs, scope="read_state")
def list_contracts(a: NoArgs) -> list[dict]:
    """All contracts: id, title, type, parties, version, effective date, governing law."""
    return [{"contract_id": c.contract_id, "title": c.title, "type": c.type, "version": c.current_version,
             "parties": c.meta.get("parties", []), "effective_date": c.meta.get("effective_date"),
             "governing_law": c.meta.get("governing_law")} for c in repo.contracts()]


@REGISTRY.tool(args=ContractArgs, scope="read_state")
def get_extraction(a: ContractArgs) -> dict:
    """Thor's current structured extraction of a contract (with confidence + citations)."""
    x = insights.extraction(a.contract_id)
    return x.model_dump(mode="json") if x else {"error": "not extracted yet"}


@REGISTRY.tool(args=NoArgs, scope="read_state")
def get_company_context(a: NoArgs) -> dict:
    """Company profile: jurisdictions, currency, risk appetite, approval threshold, priorities."""
    c = repo.company(current().company_id)
    return (c.context or {}) if c else {}


@REGISTRY.tool(args=TimelineArgs, scope="read_state")
def compute_timeline(a: TimelineArgs) -> dict:
    """Norns timeline + exposure at the simulated clock (or `as_of`)."""
    now = a.as_of or repo.sim_now()
    tls = [t for t in insights.timelines(now) if not a.contract_id or t.contract_id == a.contract_id]
    return {"as_of": now, "contracts": [{"contract_id": t.contract_id, "term_end": t.term_end,
                                         "notice_deadline": t.notice_deadline,
                                         "exposure": t.exposure.model_dump(mode="json"),
                                         "entries": [e.model_dump(mode="json") for e in t.entries[:60]]} for t in tls]}


@REGISTRY.tool(args=OptContractArgs, scope="read_state")
def get_events(a: OptContractArgs) -> list[dict]:
    """Processed real-world events (from the email feed), optionally for one contract."""
    return [e.model_dump(mode="json", exclude={"raw"}) for e in insights.events_for(a.contract_id)]


# ───────────────────────────── write tools (shared store) ─────────────────────────────
@REGISTRY.tool(args=SaveExtractionArgs, scope="write_state", llm_visible=False)
def save_extraction(a: SaveExtractionArgs) -> dict:
    """Persist Thor's extraction (citations re-verified on the way in)."""
    x = _verify_extraction(a.extraction)
    repo.put("extraction", x, rid=f"ext:{a.contract_id}:v{a.version}", contract_id=a.contract_id,
             version=a.version, status="current")
    return {"saved": True, "fields": len(insights._fields(x))}


def _verify_extraction(x: ContractExtraction) -> ContractExtraction:
    for f in insights._fields(x):
        if f.citation:
            f.citation = citations.verify(f.citation)
            if not f.citation.verified and f.status == "found":
                f.status = "unverified"
                f.confidence = min(f.confidence, 0.4)
        elif f.status == "found":
            f.status = "unverified"
            f.confidence = min(f.confidence, 0.3)
    return x


@REGISTRY.tool(args=ClarifyArgs, scope="write_state", llm_visible=False)
def request_clarification(a: ClarifyArgs) -> dict:
    """Loki → Thor clarification request on a specific clause (FR4.4)."""
    rid = new_id("clar")
    repo.put("clarification", _Rec(id=rid, status="open", **a.model_dump()), contract_id=a.contract_id)
    return {"id": rid}


class _Rec(BaseModel):
    model_config = {"extra": "allow"}
    id: str
    status: str = ""


@REGISTRY.tool(args=FindingArgs, scope="write_state", llm_visible=False)
def save_finding(a: FindingArgs) -> dict:
    """Store / update a Loki finding."""
    f = a.finding
    f.citations = citations.verify_all(f.citations)
    repo.put("finding", f, contract_id=f.contract_id)
    return {"id": f.id, "verified_citations": sum(c.verified for c in f.citations)}


@REGISTRY.tool(args=VerificationArgs, scope="write_state", llm_visible=False)
def save_verification(a: VerificationArgs) -> dict:
    """Store a Heimdall verification of a finding."""
    v = a.verification
    v.citations = citations.verify_all(v.citations)
    f = repo.get("finding", v.finding_id)
    repo.put("verification", v, contract_id=f.get("contract_id") if f else None, status=v.verdict)
    return {"id": v.id}


@REGISTRY.tool(args=RulingArgs, scope="write_state", llm_visible=False)
def save_ruling(a: RulingArgs) -> dict:
    """Store a Tyr ruling and settle the finding."""
    repo.put("ruling", a.ruling, contract_id=a.contract_id, status=a.ruling.winner)
    f = repo.get("finding", a.ruling.finding_id)
    if f:
        repo.set_status(a.ruling.finding_id, "ruled" if a.ruling.winner != "heimdall" else "withdrawn",
                        severity=a.ruling.final_severity)
    return {"id": a.ruling.id}


@REGISTRY.tool(args=ActionArgs, scope="write_state", llm_visible=False)
def draft_action(a: ActionArgs) -> dict:
    """Store a Tyr action draft (never sends anything)."""
    act = a.action
    act.citations = citations.verify_all(act.citations)
    repo.put("action", act, contract_id=act.contract_id)
    return {"id": act.id}


@REGISTRY.tool(args=AlertArgs, scope="write_state", llm_visible=False)
def create_alert(a: AlertArgs) -> dict:
    """Raise an alert (deduped by dedupe_key)."""
    repo.put("alert", a.alert, contract_id=a.alert.contract_id)
    return {"id": a.alert.id}


@REGISTRY.tool(args=ViolationArgs, scope="write_state", llm_visible=False)
def create_violation(a: ViolationArgs) -> dict:
    """Record a clause violation caused by an event, with exact clause location."""
    repo.put("violation", a.violation, contract_id=a.violation.contract_id)
    return {"id": a.violation.id}


@REGISTRY.tool(args=DependencyArgs, scope="write_state", llm_visible=False)
def save_dependency(a: DependencyArgs) -> dict:
    """Store a contract→contract edge (depends_on / conflicts_with / supersedes / governs)."""
    rid = f"dep:{a.from_contract}:{a.to_contract}:{a.kind}"
    repo.put("dependency", _Rec(id=rid, status="current", **a.model_dump()), contract_id=a.from_contract)
    return {"id": rid}


# ───────────────────────────── side-effect tools (approval-gated) ─────────────────────────────
@REGISTRY.tool(args=GmailArgs, scope="external_send", side_effect=True, requires_approval=True, pii=True,
               llm_visible=False)
def send_gmail(a: GmailArgs) -> dict:
    """Send an email from the company's Gmail. Requires an approved action."""
    from odin.email.gmail import send_message
    return send_message(current().company_id, a.to, a.subject, a.body, a.thread_id)


@REGISTRY.tool(args=GmailArgs, scope="external_send", side_effect=True, pii=True, llm_visible=False)
def send_system_reply(a: GmailArgs) -> dict:
    """System auto-reply (e.g. malformed event email template). No approval: fixed template only."""
    from odin.email.gmail import send_message
    return send_message(current().company_id, a.to, a.subject, a.body, a.thread_id)


@REGISTRY.tool(args=AmendArgs, scope="file_write", side_effect=True, requires_approval=True, llm_visible=False)
def apply_amendment(a: AmendArgs) -> dict:
    """Apply an approved amendment's redlines → new DOCX version → re-ingest (update flow)."""
    from odin.services.amend import apply
    return apply(a.action_id)


@REGISTRY.tool(args=WebhookArgs, scope="external_send", side_effect=True, llm_visible=False)
def post_webhook(a: WebhookArgs) -> dict:
    """POST a JSON notification to the configured WEBHOOK_URL (Slack-compatible 'text')."""
    url = settings().webhook_url
    if not url:
        return {"skipped": "WEBHOOK_URL not set"}
    body = {"text": f"[Odin] {a.event}: {a.payload.get('title', '')}", "event": a.event, "payload": a.payload}
    r = httpx.post(url, content=json.dumps(body, default=str), headers={"content-type": "application/json"}, timeout=10)
    return {"status": r.status_code}


# ───────────────────────────── allowlists ─────────────────────────────
READ = ("get_clause", "hybrid_search", "list_contracts", "get_extraction", "get_company_context",
        "compute_timeline", "get_events")
REGISTRY.grant("odin", "list_contracts", "get_company_context", "compute_timeline")
REGISTRY.grant("thor", "get_clause", "hybrid_search", "get_extraction", "save_extraction", "get_company_context")
REGISTRY.grant("norns", "get_extraction", "compute_timeline", "get_events", "get_clause", "get_company_context",
               "save_extraction")
REGISTRY.grant("loki", "get_clause", "hybrid_search", "get_extraction", "list_contracts", "get_company_context",
               "get_events", "request_clarification", "save_finding", "save_dependency")
REGISTRY.grant("heimdall", "get_clause", "hybrid_search", "get_extraction", "get_events", "compute_timeline",
               "list_contracts", "save_verification", "create_alert", "create_violation", "post_webhook",
               "get_company_context")
REGISTRY.grant("tyr", "get_clause", "hybrid_search", "get_extraction", "get_company_context", "compute_timeline",
               "get_events", "save_ruling", "draft_action", "create_alert")
REGISTRY.grant("synth", *READ)
REGISTRY.grant("ask", *READ)
REGISTRY.grant("system", *READ, "send_gmail", "send_system_reply", "apply_amendment", "post_webhook", "create_alert",
               "save_extraction")
