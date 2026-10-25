"""All Odin schemas — single source of truth (plan §4).

Two families:
  * LLM-facing models (what agents must return) — kept flat & JSON-schema friendly.
  * Stored records (what the shared store holds) — same models + ids/status.
`source` on every agent output distinguishes SOURCED facts (clause text) from ANALYSIS (NFR2).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, BeforeValidator, Field


def _clamp_severity(v):
    """Models sometimes answer 0 or 6; clamp into 1-5 instead of failing the whole step."""
    return v if v is None else min(5, max(1, round(float(v))))


def _clamp_unit(v):
    """Scores in 0-1; a model answering 85 means 0.85."""
    if v is None:
        return v
    v = float(v)
    return min(1.0, max(0.0, v / 100 if 1 < v <= 100 else v))


Score5 = Annotated[int, BeforeValidator(_clamp_severity), Field(ge=1, le=5)]
Unit = Annotated[float, BeforeValidator(_clamp_unit), Field(ge=0, le=1)]


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


# ───────────────────────────── shared primitives ─────────────────────────────
class Money(BaseModel):
    amount: float
    currency: str = "INR"


class Citation(BaseModel):
    contract_id: str = Field(description="CONTRACT ID from the cover block, e.g. MSA-2026-001")
    clause_number: str = Field(description='Clause number exactly as printed, e.g. "2.2" or "SCHEDULE A"')
    quote: str = Field(description="Verbatim supporting text copied from the clause (<= 300 chars)")
    page: Optional[int] = None
    version: Optional[int] = None
    verified: bool = False          # set by the citation guard, never by the LLM


FieldStatus = Literal["found", "ambiguous", "missing", "contradictory", "unverified"]
Severity = Literal["info", "low", "medium", "high", "critical"]
SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


# ───────────────────────────── inputs ─────────────────────────────
class Party(BaseModel):
    name: str
    role: Literal["company", "counterparty", "unknown"] = "unknown"
    alias: Optional[str] = None
    capacity: Optional[str] = Field(None, description='Role this party plays as written in the contract, '
                                    'e.g. "Controller", "Processor", "Supplier", "Customer", "Landlord"')


class CompanyContext(BaseModel):
    name: str = ""
    industry: str = ""
    jurisdictions: list[str] = []
    base_currency: str = "INR"
    fiscal_year_start: str = "04-01"
    risk_appetite: Literal["low", "medium", "high"] = "medium"
    approval_threshold: Optional[Money] = None
    contacts: list[str] = []
    priorities: str = ""
    critical_deps: str = ""
    raw_text: str = ""


class CoverMeta(BaseModel):
    """Parsed from the contract cover block (authoring spec §3.1)."""
    contract_id: str
    title: str = ""
    type: str = "other"
    effective_date: Optional[date] = None
    parties: list[Party] = []
    governing_law: str = ""
    version: int = 1
    supersedes: Optional[str] = None


class Clause(BaseModel):
    id: str
    contract_id: str
    version: int
    number: str
    heading: str = ""
    text: str
    page: int = 1
    char_start: int = 0
    char_end: int = 0
    clause_type: str = "general"


# ───────────────────────────── Thor (extraction) ─────────────────────────────
class Sourced(BaseModel):
    """Envelope every extracted value travels in (FR2.2/FR2.3)."""
    confidence: Unit
    citation: Optional[Citation] = None
    status: FieldStatus = "found"
    note: str = ""
    source: Literal["sourced"] = "sourced"


class TermField(Sourced):
    effective_date: Optional[date] = None
    term_months: Optional[int] = None
    end_date: Optional[date] = None


class RenewalField(Sourced):
    auto_renew: Optional[bool] = None
    renewal_period_months: Optional[int] = None
    notice_days: Optional[int] = Field(None, description="Days of notice needed before expiry to stop renewal")
    renewal_value: Optional[Money] = Field(None, description="Committed spend for one renewal period, if stated")


class PaymentField(Sourced):
    description: str = ""
    payer: str = ""
    payee: str = ""
    amount: Optional[Money] = None
    frequency: Literal["one_time", "monthly", "quarterly", "half_yearly", "annual", "unknown"] = "unknown"
    first_due: Optional[date] = None
    due_rule: str = Field("", description='e.g. "within 30 days of invoice", "5th of each month"')
    late_fee_pct_per_month: Optional[float] = None
    late_fee_flat: Optional[Money] = None
    first_due_at: Optional[datetime] = Field(None, description="Exact deadline in UTC (ISO 8601 with Z) when the contract states a time of day; else null")


class ObligationField(Sourced):
    owner: str = ""
    description: str = ""
    due_rule: str = ""
    due_date: Optional[date] = None
    due_at: Optional[datetime] = Field(None, description="Exact deadline in UTC (ISO 8601 with Z) when the contract states a time of day; else null")
    recurring: bool = False


class PenaltyField(Sourced):
    trigger: str = ""
    amount: Optional[Money] = None
    pct: Optional[float] = Field(None, description="Percent of a base (fees, contract value, ...)")
    pct_base: str = ""
    cap: Optional[Money] = None
    kind: Literal["service_credit", "delay_charge", "late_interest", "liquidated_damages", "indemnity",
                  "other"] = "other"
    basis: Literal["per_incident", "per_day", "per_month", "one_time", "other"] = Field(
        "other", description="What `amount` (or `pct`) is charged per")
    cap_period: Literal["per_incident", "per_month", "per_lot", "per_invoice", "per_year", "total", ""] = Field(
        "", description="Period or unit the `cap` applies to")
    direction: Literal["payable", "receivable", "unknown"] = Field(
        "unknown", description="payable = the company pays it; receivable = the company receives or recovers it")


class ComplianceField(Sourced):
    requirement: str = ""
    regulation: str = ""


class TerminationField(Sourced):
    who: str = ""
    kind: Literal["convenience", "cause", "other"] = "other"
    notice_days: Optional[int] = None
    conditions: str = ""


class SimpleField(Sourced):
    value: str = ""


class PeriodField(Sourced):
    """A stated time limit that is not a payment or renewal, e.g. a cure, claim, warranty or reporting period."""
    purpose: str = Field(description='Short snake_case purpose, e.g. "cure", "claim", "warranty", "survival", '
                         '"reporting", "acknowledgement", "approval_lead", "restore", "return", "replacement", '
                         '"payment", "notice", "credit_threshold"')
    value: float
    unit: Literal["minutes", "hours", "days", "business_days", "months", "years"]
    starts_from: str = Field("", description='Trigger the period runs from, e.g. "receipt of notice"')
    comparison: Literal["within", "at_least", "more_than", "exactly", ""] = ""


class RelatedContractField(Sourced):
    contract_ref: str = Field(description="Contract ID exactly as written, e.g. C01")
    relation: Literal["depends_on", "supplies", "replaces", "does_not_replace", "separate_agreement", "amends",
                      "related"]


class NoticeField(Sourced):
    address: str = Field("", description="Address or email for formal notices to the counterparty")
    authorized_sender: str = Field("", description="Person named as authorised to send notices, if any")


class AmbiguityFlag(BaseModel):
    clause_number: str
    kind: Literal["ambiguous", "missing", "contradictory"]
    note: str
    related_clauses: list[str] = []


class ContractExtraction(BaseModel):
    """Thor's output for one contract version."""
    parties: list[Party] = []
    term: Optional[TermField] = None
    renewal: Optional[RenewalField] = None
    payments: list[PaymentField] = []
    obligations: list[ObligationField] = []
    penalties: list[PenaltyField] = []
    compliance: list[ComplianceField] = []
    termination: list[TerminationField] = []
    liability_cap: Optional[SimpleField] = None
    governing_law: Optional[SimpleField] = None
    forum: Optional[SimpleField] = Field(None, description="City or seat of the courts or arbitration")
    notice: Optional[NoticeField] = None
    periods: list[PeriodField] = []
    related_contracts: list[RelatedContractField] = []
    flags: list[AmbiguityFlag] = []


# Every Sourced field of ContractExtraction, in one place (merge, digest, citation guard).
EXTRACTION_ONE_FIELDS = ("term", "renewal", "liability_cap", "governing_law", "forum", "notice")
EXTRACTION_LIST_FIELDS = ("payments", "obligations", "penalties", "compliance", "termination", "periods",
                          "related_contracts")


class ClauseReextraction(BaseModel):
    """Thor's answer to a targeted clarification (FR2.4)."""
    answer: str
    updated_fields: ContractExtraction = Field(
        default_factory=ContractExtraction,
        description="Only the fields affected by this clause; leave others empty")
    resolved: bool


# ───────────────────────────── Norns (timeline) ─────────────────────────────
TimelineKind = Literal["payment", "renewal", "notice_deadline", "penalty_trigger", "expiry",
                       "obligation", "termination_window"]


class TimelineEntry(BaseModel):
    id: str
    contract_id: str
    date: date
    kind: TimelineKind
    title: str
    status: Literal["past", "due", "upcoming", "missed", "done"] = "upcoming"
    amount: Optional[Money] = None
    citation: Optional[Citation] = None
    due_at: Optional[datetime] = None        # exact UTC deadline when the contract gives a time of day
    owner: str = ""
    source: Literal["analysis"] = "analysis"


class ExposureLine(BaseModel):
    contract_id: str
    label: str
    amount: Money
    month: Optional[str] = None       # YYYY-MM for heatmap
    clause_type: str = "general"
    citation: Optional[Citation] = None


class Exposure(BaseModel):
    as_of: date
    expected: float
    worst_case: float
    currency: str
    lines: list[ExposureLine] = []
    assumptions: list[str] = []
    source: Literal["analysis"] = "analysis"


# ───────────────────────────── Loki (adversarial) ─────────────────────────────
FindingKind = Literal["ambiguity", "one_sided", "hidden_liability", "conflict", "missing_protection",
                      "event_breach"]


class LokiFindingDraft(BaseModel):
    kind: FindingKind
    claim: str = Field(description="What the counterparty's lawyer would argue")
    attack_path: str = Field(description="Step-by-step how the clause is exploited")
    citations: list[Citation]
    severity: Score5
    likelihood: Unit
    other_contract_ids: list[str] = Field(default=[], description="For cross-contract conflicts")


class ClarificationDraft(BaseModel):
    clause_number: str
    field_path: str = Field(description='Extraction field in doubt, e.g. "renewal.notice_days"')
    question: str


class DependencyDraft(BaseModel):
    from_contract: str = Field(description="For depends_on: the DEPENDENT contract (it breaks if to_contract fails)")
    to_contract: str = Field(description="For depends_on: the contract it relies on. E.g. a customer SLA "
                                         "(from) depends_on the hosting agreement (to); never the reverse")
    kind: Literal["depends_on", "conflicts_with", "supersedes", "governs"] = "depends_on"
    reason: str
    citations: list[Citation] = []


class LokiOutput(BaseModel):
    findings: list[LokiFindingDraft] = []
    clarifications: list[ClarificationDraft] = []
    dependencies: list[DependencyDraft] = []


class LokiRebuttal(BaseModel):
    finding_id: str
    position: Literal["maintain", "revise", "withdraw"]
    argument: str
    # 0 means "no new severity" (e.g. withdrawn); anything else is clamped into 1-5
    revised_severity: Annotated[Optional[int], BeforeValidator(
        lambda v: None if v in (None, 0, "0") else _clamp_severity(v))] = Field(None, ge=1, le=5)


class LokiRebuttals(BaseModel):
    rebuttals: list[LokiRebuttal] = []


class Finding(LokiFindingDraft):
    id: str
    contract_id: str                      # or "cross"
    status: Literal["open", "verified", "challenged", "ruled", "withdrawn"] = "open"
    event_id: Optional[str] = None
    source: Literal["analysis"] = "analysis"


# ───────────────────────────── Heimdall (verify / events) ─────────────────────────────
class VerificationDraft(BaseModel):
    finding_id: str
    verdict: Literal["support", "challenge", "insufficient"]
    rationale: str
    citations: list[Citation] = []


class HeimdallVerifications(BaseModel):
    verifications: list[VerificationDraft] = []


class Verification(VerificationDraft):
    id: str
    round: int = 0
    evidence_events: list[str] = []
    source: Literal["analysis"] = "analysis"


EventType = Literal["PAYMENT_MADE", "PAYMENT_LATE", "PAYMENT_MISSED", "INVOICE_RECEIVED", "SERVICE_OUTAGE",
                    "SLA_BREACH", "DELIVERY_LATE", "DELIVERY_RECEIVED", "REGULATORY_CHANGE", "PRICE_CHANGE",
                    "TERMINATION_NOTICE_RECEIVED", "RENEWAL_NOTICE_RECEIVED", "PARTY_CHANGE",
                    "FORCE_MAJEURE", "DISPUTE_RAISED", "CUSTOM"]
EVENT_TYPES: tuple[str, ...] = EventType.__args__  # type: ignore[attr-defined]


class ParsedEvent(BaseModel):
    """Email body → event (strict parser or LLM fallback)."""
    event_type: EventType
    occurred_at: datetime
    contract_ids: list[str] = []
    counterparty: str = ""
    amount: Optional[Money] = None
    reference: str = ""
    severity_hint: str = ""
    description: str = ""
    external_id: str = ""


class Event(ParsedEvent):
    id: str
    gmail_msg_id: Optional[str] = None
    sender: str = ""
    subject: str = ""
    raw: str = ""
    parse_method: Literal["strict", "llm", "manual", "demo"] = "strict"
    parse_confidence: float = 1.0
    status: Literal["received", "processing", "processed", "rejected", "noise", "quarantined"] = "received"
    reject_reason: str = ""
    scenario_id: Optional[str] = None


class ViolationDraft(BaseModel):
    contract_id: str
    clause_number: str
    quote: str = Field(description="Verbatim text of the clause that is breached")
    breach_type: str = Field(description='e.g. "late payment", "SLA breach", "exclusivity breach"')
    breached_by: Literal["company", "counterparty", "unclear"]
    exposure: Optional[Money] = None
    explanation: str


class EventMapping(BaseModel):
    """Heimdall's reading of one event (FR5.1/5.3)."""
    is_noise: bool
    noise_reason: str = ""
    affected_contract_ids: list[str] = []
    affected_clauses: list[Citation] = []
    effect: str = ""
    exposure_delta: Optional[Money] = None
    violations: list[ViolationDraft] = []
    alert_severity: Severity = "medium"
    alert_title: str = ""


class Violation(BaseModel):
    id: str
    event_id: str
    contract_id: str
    version: int
    clause_id: Optional[str] = None
    clause_number: str
    quote: str
    page: Optional[int] = None
    bboxes: list[list[float]] = []      # [page, x0, y0, x1, y1]
    breach_type: str
    breached_by: str
    exposure: Optional[Money] = None
    explanation: str = ""
    ruling_id: Optional[str] = None
    status: Literal["suspected", "confirmed", "dismissed"] = "suspected"
    source: Literal["analysis"] = "analysis"


# ───────────────────────────── Tyr (rulings / actions) ─────────────────────────────
class RulingDraft(BaseModel):
    finding_id: str
    winner: Literal["loki", "heimdall", "split"]
    rationale: str
    final_severity: Score5
    confidence: Unit


class TyrRulings(BaseModel):
    rulings: list[RulingDraft] = []


class Ruling(RulingDraft):
    id: str
    source: Literal["analysis"] = "analysis"


ActionKind = Literal["renewal_notice", "non_renewal_notice", "termination_notice", "breach_notice",
                     "payment_instruction", "amendment", "escalation_memo"]


class ClauseRedline(BaseModel):
    clause_number: str
    before: str
    after: str
    reason: str


class ActionDraftOut(BaseModel):
    kind: ActionKind
    to: str = Field(description="Recipient party / email if known")
    subject: str
    body_md: str = Field(description="Ready-to-send text that cites exact clause numbers")
    citations: list[Citation]
    confidence: Unit
    est_exposure_avoided: Optional[Money] = None
    deadline: Optional[date] = None
    redlines: list[ClauseRedline] = []
    leverage_notes: str = ""
    related_finding_ids: list[str] = []
    related_violation_ids: list[str] = []


class TyrActions(BaseModel):
    actions: list[ActionDraftOut] = []


class ActionDraft(ActionDraftOut):
    id: str
    contract_id: str
    needs_human_approval: bool = True
    status: Literal["draft", "approved", "rejected", "sent", "applied"] = "draft"
    priority: float = 0.0
    event_id: Optional[str] = None
    source: Literal["analysis"] = "analysis"


# ───────────────────────────── alerts / reports ─────────────────────────────
class Alert(BaseModel):
    id: str
    dedupe_key: str
    severity: Severity
    kind: str
    title: str
    why: str = ""
    contract_id: Optional[str] = None
    due_date: Optional[date] = None
    citations: list[Citation] = []
    event_id: Optional[str] = None
    violation_id: Optional[str] = None
    status: Literal["open", "acknowledged", "snoozed", "resolved"] = "open"
    snooze_until: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReportSummary(BaseModel):
    executive_summary: str
    key_risks: list[str] = []
    recommended_next_steps: list[str] = []


class AskAnswer(BaseModel):
    answer: str
    citations: list[Citation] = []
    insufficient_evidence: bool = False


# ───────────────────────────── orchestration ─────────────────────────────
WSStatus = Literal["pending", "running", "blocked", "done", "partial", "failed"]


class Workstream(BaseModel):
    id: str
    contract_id: str            # or "cross"
    status: WSStatus = "pending"
    tasks: list[str] = []
    reason: str = ""
    evidence_score: float = 0.0


class WorkPlan(BaseModel):
    run_id: str
    workstreams: list[Workstream] = []


class AgentMessage(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    run_id: str
    sender: str
    receiver: str
    kind: str                   # extract | clarify | attack | verify | rebut | rule | action | alert | plan | event
    summary: str
    payload: dict = {}
    contract_id: Optional[str] = None
    ts: datetime = Field(default_factory=datetime.utcnow)
