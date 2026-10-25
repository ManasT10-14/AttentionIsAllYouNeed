"""Smallest checks that fail if the core logic breaks. No DB, no network.
Run: backend/.venv/Scripts/python -m pytest backend/tests -q"""
from datetime import date, datetime, timezone

import pytest

from odin.core import budget as budget_mod
from odin.core.models import (AskAnswer, Citation, ContractExtraction, EventMapping, HeimdallVerifications,
                              LokiOutput, LokiRebuttals, Money, PaymentField, RenewalField, ReportSummary, TermField,
                              TyrActions, TyrRulings)
from odin.email import event_parser
from odin.ingest.parse import parse_money, parse_pdf, text_to_pdf
from odin.llm.fake import fake_instance
from odin.services.timeline import ContractInputs, compute

CONTRACT = """CONTRACT TITLE: Test Lease
CONTRACT ID: LEASE-T-1
CONTRACT TYPE: lease
EFFECTIVE DATE: 2025-01-01
PARTY A: Acme Corp (the "Tenant")
PARTY B: Landlord LLP (the "Landlord")
GOVERNING LAW: India
VERSION: 1

1. TERM AND RENEWAL
1.1 The lease continues for 24 months.
1.2 It renews automatically for 12 months unless notice is given at least 60 days before expiry.
2. RENT
2.1 Rent of INR 4,50,000 is payable monthly, interest on late payment
30 days after the due date at 18% per annum.
2.5 times nothing - this wrapped line must stay inside clause 2.1? no: it is a valid sub-clause number.
SCHEDULE A - FEES
Row 1: rent.
"""


def test_segmenter_and_cover(tmp_path):
    pdf = tmp_path / "c.pdf"
    text_to_pdf(CONTRACT, pdf)
    doc = parse_pdf(pdf, "FALLBACK")
    assert doc.cover.contract_id == "LEASE-T-1"
    assert doc.cover.effective_date == date(2025, 1, 1)
    assert [p.role for p in doc.cover.parties] == ["company", "counterparty"]
    nums = [c.number for c in doc.clauses]
    assert nums[:5] == ["1", "1.1", "1.2", "2", "2.1"]
    assert "30 days after the due date" in doc.clauses[4].text      # wrapped line "30 days…" is NOT a clause
    assert nums[-1] == "SCHEDULE A"
    assert all(c.bboxes and c.page == 1 for c in doc.clauses)
    assert doc.clauses[1].clause_type == "renewal"


def test_dates_iso_not_dayfirst():
    from odin.ingest.parse import parse_date
    assert parse_date("2026-04-01") == date(2026, 4, 1)
    assert parse_date("1 March 2026") == date(2026, 3, 1)
    assert parse_date("05/04/2026") == date(2026, 4, 5)     # Indian dd/mm


def test_money():
    assert parse_money("INR 5,00,000").amount == 500000
    assert parse_money("$12,000.50").currency == "USD"
    assert parse_money("no money") is None


def test_email_parser_ok():
    ev = event_parser.parse("[ODIN-EVENT] PAYMENT_LATE MSA-1",
                            "EVENT_TYPE: PAYMENT_LATE\nOCCURRED_AT: 2026-11-03T10:30:00+05:30\nAMOUNT: INR 2,50,000\n"
                            "DESCRIPTION:\nline one\nline two\n\n> quoted reply\n")
    assert ev.event_type == "PAYMENT_LATE" and ev.contract_ids == ["MSA-1"]
    assert ev.amount.amount == 250000 and ev.description == "line one\nline two"


def test_email_parser_rejects():
    with pytest.raises(event_parser.EventParseError) as e:
        event_parser.parse("[ODIN-EVENT] PAYMNT_LATE X", "CONTRACT_ID: X\n")
    assert len(e.value.problems) == 2          # bad type + missing OCCURRED_AT
    assert "OCCURRED_AT" in event_parser.reply_body(e.value.problems)


def _cite(n):
    return Citation(contract_id="L", clause_number=n, quote="q", verified=True)


def test_timeline_notice_deadline_and_worst_case():
    x = ContractExtraction(
        term=TermField(confidence=1, citation=_cite("1.1"), effective_date=date(2025, 1, 1), term_months=24),
        renewal=RenewalField(confidence=1, citation=_cite("1.2"), auto_renew=True, renewal_period_months=12, notice_days=60),
        payments=[PaymentField(confidence=1, citation=_cite("2.1"), payee="Landlord LLP", payer="Acme Corp",
                               amount=Money(amount=450000), frequency="monthly", first_due=date(2025, 1, 5),
                               late_fee_pct_per_month=1.5)])
    from odin.core.models import Event
    late = Event(id="e", event_type="PAYMENT_LATE", occurred_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
                 contract_ids=["L"])
    ci = ContractInputs(contract_id="L", extraction=x, governing_law="India", events=[late], company_names=["Acme Corp"])
    tl = compute(ci, date(2026, 10, 25))
    assert tl.term_end == date(2026, 12, 31)
    assert tl.notice_deadline <= date(2026, 11, 1) and tl.notice_deadline.weekday() < 5   # Sunday → Friday
    kinds = {e.kind for e in tl.entries}
    assert {"expiry", "notice_deadline", "renewal", "payment", "penalty_trigger"} <= kinds
    assert any(e.status == "missed" for e in tl.entries if e.kind == "payment")
    assert tl.exposure.worst_case >= tl.exposure.expected > 0
    # sending the non-renewal notice removes the renewal lock-in
    acted = compute(ContractInputs(**{**ci.__dict__, "actions": [{"kind": "non_renewal_notice"}]}), date(2026, 10, 25))
    assert acted.exposure.expected < tl.exposure.expected


def test_receivables_are_not_exposure():
    x = ContractExtraction(
        term=TermField(confidence=1, effective_date=date(2026, 4, 1), term_months=24),
        payments=[PaymentField(confidence=1, payee="Acme Corp", payer="Client", amount=Money(amount=1200000),
                               frequency="monthly", first_due=date(2026, 4, 10))])
    tl = compute(ContractInputs(contract_id="C", extraction=x, company_names=["Acme Corp"]), date(2026, 10, 25))
    assert tl.exposure.expected == 0
    assert any(e.title.startswith("Receivable") for e in tl.entries)


def test_budget_stops():
    b = budget_mod.override("t-run", max_agent_calls=2)
    b.charge("thor")
    b.check()
    b.charge("loki")
    with pytest.raises(budget_mod.BudgetExceeded):
        b.check()
    budget_mod.release("t-run")


@pytest.mark.parametrize("schema", [ContractExtraction, LokiOutput, LokiRebuttals, HeimdallVerifications, EventMapping,
                                    TyrRulings, TyrActions, ReportSummary, AskAnswer])
def test_fake_llm_builds_every_schema(schema):
    assert isinstance(fake_instance(schema), schema)


def test_pmap_keeps_run_ctx():
    from odin.agents.base import pmap
    from odin.core.context import current, run_ctx
    with run_ctx("co-x", run_id="r1"):
        assert pmap(lambda i: (current().company_id, i), [1, 2, 3]) == [("co-x", 1), ("co-x", 2), ("co-x", 3)]


def test_registry_allowlist_and_approval():
    from odin.tools.registry import REGISTRY, ApprovalRequired, ToolDenied
    import odin.tools.core  # noqa: F401
    with pytest.raises(ToolDenied):
        REGISTRY.invoke("loki", "send_gmail", {"to": "x@y.z", "subject": "s", "body": "b"})
    with pytest.raises(ApprovalRequired):
        REGISTRY._check_approval(None)
    loki_tools = {t.name for t in REGISTRY.langchain_tools("loki", ["get_clause", "save_finding", "send_gmail"])}
    assert loki_tools == {"get_clause"}       # writes / side effects never exposed to the LLM
