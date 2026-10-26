"""Functional bundle/replay regressions: actual source parsing, isolated DB, no evaluator files."""
from contextlib import contextmanager
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from odin.core.context import run_ctx
from odin.db import repo
from odin.db.tables import Base, Company
from odin.ingest import service as ingestion
from odin.retrieval import hybrid
from odin.services import bundle, simulation


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    @contextmanager
    def db():
        with factory() as s:
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
    for module in (repo, bundle, simulation, ingestion, hybrid):
        monkeypatch.setattr(module, "db", db)
    monkeypatch.setattr(ingestion, "DATA_DIR", tmp_path)
    monkeypatch.setattr(ingestion, "odin_config", lambda: {"retrieval": {"dense_enabled": False}})
    with db() as s:
        s.add_all([Company(id="pack-test"), Company(id="other")])
    return db


def test_inventory_includes_every_pdf_and_manifest_source():
    files = bundle.inventory()
    assert len([x for x in files if x["path"].endswith(".pdf")]) == 8
    assert all(len(x["sha256"]) == 64 and x["size"] > 0 for x in files)


def test_import_exact_quotes_relations_and_idempotence(workspace):
    first = bundle.import_bundle("pack-test")
    assert first["counts"]["documents"] == 8
    assert first["counts"]["clauses"] > 200
    assert first["counts"]["ledger"] > 0 and first["counts"]["holidays"] > 0
    with run_ctx("pack-test"):
        assert repo.sim_now() == date(2027, 1, 15)
        assert repo.query("event") == []
        assert {o["number"] for o in repo.query("clause_override") if o["doc"] == "A2"} == {"3.1", "3.2"}
        for c in repo.contracts():
            v = repo.version_row(c.contract_id, c.current_version)
            source = (bundle.PACK / f"bundle/contracts/{c.contract_id}.txt").read_text(encoding="utf-8")
            assert v.text == source
            for cl in repo.clauses(c.contract_id):
                assert v.text[cl.char_start:cl.char_end] == cl.text
                assert cl.text in source
        assert any(r["relation"] == "incorporates" and r["to_doc"] == "STD" for r in first["relations"])
        assert any(r["relation"] == "amends" and r["to_doc"] == "A2" for r in first["relations"])
    again = bundle.import_bundle("pack-test")
    assert all(r["duplicate"] for r in again["results"])
    with run_ctx("other"):
        assert not repo.contracts() and not repo.query("ledger")


def test_staged_replay_quarantine_checkpoints_reset(workspace):
    bundle.import_bundle("pack-test")
    a = simulation.load_drop("pack-test", 1)
    assert a["accepted"] == 10
    assert simulation.load_drop("pack-test", 1)["duplicate"]
    with run_ctx("pack-test"):
        assert not repo.query("event")
    # Use real replay/storage with a stub assessment: never pretend a model ran.
    simulation.advance("pack-test", date(2027, 3, 15), assess=False)
    with run_ctx("pack-test"):
        assert repo.sim_now() == date(2027, 3, 15)
        assert all(e["occurred_at"][:10] <= "2027-03-15" for e in repo.query("event"))
        assert len(repo.query("simulation_checkpoint")) == 1
        assert repo.query("simulation_checkpoint")[0]["analysis_complete"] is False
    with pytest.raises(ValueError, match="Drop 2"):
        simulation.advance("pack-test", date(2027, 6, 1), assess=False)
    loaded = simulation.load_drop("pack-test", 2)
    assert loaded["rejected"] == 1
    simulation.advance("pack-test", date(2027, 9, 15), assess=False)
    with run_ctx("pack-test"):
        snaps = repo.query("simulation_checkpoint")
        assert len(snaps) == 3
        assert all(e.get("occurred_at", "")[:10] <= cp["checkpoint"] for cp in snaps for e in cp["events"] if e.get("occurred_at"))
        count = len(repo.query("event"))
        assert count == 19
    simulation.advance("pack-test", date(2027, 9, 15), assess=False)
    with run_ctx("pack-test"):
        assert len(repo.query("event")) == count
    simulation.reset("pack-test")
    with run_ctx("pack-test"):
        assert not repo.query("event") and not repo.query("simulation_checkpoint")
        assert len(repo.contracts()) == 8
        assert repo.sim_now() == date(2027, 1, 15)


def test_holiday_schedule_is_authoritative():
    assert simulation.add_business_days(date(2027, 1, 15), 1, [{"date": "2027-01-18", "observed_by": "Quillhub"}]) == date(2027, 1, 19)
    assert simulation.add_business_days(date(2027, 1, 15), 1, [{"date": "2027-01-18", "observed_by": "Another Company"}]) == date(2027, 1, 18)

def test_pack_citations_restore_source_whitespace_and_reject_changed_words(workspace):
    from odin.core import citations
    from odin.core.models import Citation
    bundle.import_bundle("pack-test")
    with run_ctx("pack-test"):
        row = repo.clause_by_number("A2", "3.2")
        exact = row.text[:180]
        assert citations.verify(Citation(contract_id="A2", clause_number="3.2", quote=exact)).verified
        reflowed = " ".join(exact.split())
        assert reflowed not in row.text
        fixed = citations.verify(Citation(contract_id="A2", clause_number="3.2", quote=reflowed))
        assert fixed.verified and fixed.quote in row.text
        assert not citations.verify(Citation(contract_id="A2", clause_number="3.2", quote=reflowed + " fabricated condition")).verified


def test_api_handlers_scope_permissions_shapes_and_date_validation(workspace, monkeypatch):
    from fastapi import FastAPI, HTTPException
    from odin.api import pack
    from odin.api.deps import require_role
    from pydantic import ValidationError
    from types import SimpleNamespace
    monkeypatch.setattr(pack, "db", workspace)
    app = FastAPI()
    app.include_router(pack.router, prefix="/api")
    assert "/api/simulation/advance" in app.openapi()["paths"]
    user = SimpleNamespace(id="test", company_id="pack-test", role="admin")
    assert pack.get_simulation(user)["initialized"] is False
    response = pack.import_bundle(analyze=False, u=user)
    assert response["counts"]["documents"] == 8
    assert pack.get_simulation(user)["sim_now"] == "2027-01-15"
    assert isinstance(pack.ledger(user), list)
    assert len(pack.holidays(user)) > 0
    with pytest.raises(HTTPException) as exc:
        pack.play(pack.Play(until=date(2027,3,15)), user)
    assert exc.value.status_code == 400
    assert pack.load_drop(1, user)["accepted"] == 10
    with pytest.raises(HTTPException):
        pack.load_drop(3, user)
    with pytest.raises(HTTPException):
        pack.advance(pack.Advance(to=date(2026,1,1)), user)
    with pytest.raises(ValidationError):
        pack.Advance(to="nonsense")
    assert pack.reset(user)["sim_now"] == "2027-01-15"
    user.role = "viewer"
    with pytest.raises(HTTPException) as exc:
        require_role("admin")(user)
    assert exc.value.status_code == 403
    user.company_id = "other"
    assert pack.ledger(user) == [] and pack.checkpoints(user) == []


def test_acceptance_deadline_uses_actual_delivery_and_observed_holidays():
    from odin.core.models import ContractExtraction, MilestoneField, Event
    from odin.services.timeline import ContractInputs, compute
    from datetime import datetime, timezone
    extraction = ContractExtraction(milestones=[MilestoneField(name="M2", acceptance_rule="ten (10) business days", confidence=1)])
    ci = ContractInputs("SYNTH", extraction, holidays=[{"date": "2027-01-18", "observed_by": "Quillhub"}],
                        events=[Event(id="test", event_type="DELIVERY_RECEIVED", occurred_at=datetime(2027,1,15,tzinfo=timezone.utc),
                                      subject="M2 delivered")])
    deadline = [e for e in compute(ci, date(2027,1,15)).entries if "acceptance review" in e.title]
    assert len(deadline) == 1 and deadline[0].date == date(2027,2,1)
    ci.events[0].event_type = "CUSTOM"
    assert not [e for e in compute(ci, date(2027,1,15)).entries if "acceptance review" in e.title]

def test_recheck_repairs_whitespace_but_preserves_false_claims_and_confidence(workspace, monkeypatch):
    from odin.services import citation_recheck
    from odin.db.tables import Record
    monkeypatch.setattr(citation_recheck, "db", workspace)
    bundle.import_bundle("pack-test")
    with run_ctx("pack-test"):
        cl = repo.clause_by_number("A2", "3.2")
        quote = " ".join(cl.text[:180].split())
        bundle.save("extraction", "synthetic", {"terms": [
            {"status":"unverified", "confidence":0.4, "citation":{"contract_id":"A2", "clause_number":"3.2", "quote":quote, "verified":False}},
            {"status":"unverified", "confidence":0.3, "citation":{"contract_id":"A2", "clause_number":"3.2", "quote":"Invented unlimited credit", "verified":False}}]})
        out = citation_recheck.recheck("pack-test")
        assert out["repaired"] == 1 and out["unverified"] == 1
        data = repo.get("extraction", "synthetic")["terms"]
        assert data[0]["citation"]["quote"] in cl.text and data[0]["status"] == "found"
        assert data[0]["confidence"] == 0.4
        assert not data[1]["citation"]["verified"] and data[1]["status"] == "unverified"


def test_interrupted_runs_recover_without_claiming_completion(workspace, monkeypatch):
    from odin.services import runs
    from odin.db.tables import Run, Record
    monkeypatch.setattr(runs,"db",workspace)
    with workspace() as session:
        session.add(Run(id="old", company_id="pack-test", kind="analysis", status="running"))
        session.add(Run(id="done", company_id="pack-test", kind="analysis", status="done"))
        session.add(Record(id="pack-test|event", company_id="pack-test", kind="event", status="processing", data={"id":"event","status":"processing"}))
    assert runs.recover_interrupted_runs() == 1
    with workspace() as session:
        assert session.get(Run,"old").status == "failed"
        assert session.get(Run,"done").status == "done"
        assert session.get(Record,"pack-test|event").data["impact_review_required"] is True


def test_timeline_returns_real_ledger_history_and_separate_projections(workspace, monkeypatch):
    from odin.api import routes
    from types import SimpleNamespace
    bundle.import_bundle("pack-test")
    user = SimpleNamespace(company_id="pack-test",role="admin")
    data = routes.timeline(date(2027,1,15), None, user)
    assert len(data["history"]) > 0
    assert all(h["date"] <= "2027-01-15" and h["source"] == "ledger" for h in data["history"])
    assert len(data["unanalysed_contracts"]) == 8
    assert data["projections"] == []


def test_canonical_span_never_changes_words_numbers_or_ambiguous_repetitions():
    from odin.core.citations import canonical_span
    assert canonical_span("Pay 15 days after receipt", "Pay 15\n   days after receipt") == "Pay 15\n   days after receipt"
    assert canonical_span("Pay 30 days after receipt", "Pay 15\n   days after receipt") is None
    assert canonical_span("Pay fifteen days", "Pay 15 days") is None
    assert canonical_span("Pay 15 days", "Pay 15\n days and Pay 15\n  days") is None

def test_monthly_invoice_dates_apply_stated_net_period_and_do_not_use_effective_day():
    from odin.core.models import PaymentField, Citation, ContractExtraction, Money
    from odin.services.timeline import ContractInputs, compute
    p = PaymentField(confidence=1, payer="Customer", payee="Supplier", frequency="monthly",
        amount=Money(amount=8000,currency="USD"), first_due=date(2027,1,1),
        citation=Citation(contract_id="SYNTH",clause_number="C",quote="Invoices on the first business day of each calendar month. Payment Period: 30 days from invoice date."))
    ci = ContractInputs("SYNTH",ContractExtraction(payments=[p]),effective_date=date(2027,1,1),currency="USD",
                        holidays=[{"date":"2027-01-01","observed_by":"All"}])
    entries = [e for e in compute(ci,date(2027,1,1)).entries if e.kind == "payment"]
    assert entries[0].date == date(2027,2,3)  # Supplied holiday moves the invoice to 4 January, then the 30-day period applies.
