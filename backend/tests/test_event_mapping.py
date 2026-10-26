"""Synthetic relevance regressions; no live email, model calls or external notices."""
from copy import deepcopy
from datetime import date
import pytest
from odin.agents import heimdall
from odin.core.context import run_ctx
from odin.core.models import EventMapping
from odin.retrieval import evidence


@pytest.fixture
def mapping(monkeypatch):
    event = {"id": "evt-test", "event_type": "PAYMENT_MADE", "contract_ids": [],
             "subject": "Payment confirmation", "raw": "Thanks for the update", "description": "Paid", "occurred_at": "2026-10-26"}
    saved, prompts, tools = [], [], []
    monkeypatch.setattr(heimdall.repo, "contracts", lambda: [])
    monkeypatch.setattr(heimdall.repo, "query", lambda *a, **kw: [])
    monkeypatch.setattr(heimdall.insights, "families", lambda: {})
    monkeypatch.setattr(heimdall.insights, "family_of", lambda cid: (cid, [cid]))
    result = EventMapping(is_noise=True, noise_reason="No breach occurred")
    monkeypatch.setattr(heimdall.repo, "get", lambda *a: deepcopy(event))
    monkeypatch.setattr(heimdall.repo, "sim_now", lambda: date(2026, 10, 26))
    monkeypatch.setattr(heimdall.repo, "set_status", lambda *a, **kw: saved.append((a, kw)))
    monkeypatch.setattr(heimdall.insights, "cascade", lambda cid: [])
    monkeypatch.setattr(heimdall, "say", lambda *a, **kw: None)
    monkeypatch.setattr(heimdall, "tool", lambda name, args: [{"contract_id": "C01", "title": "Agreement"}] if name == "list_contracts" else tools.append((name, args)))
    monkeypatch.setattr(evidence, "retrieve", lambda *a, **kw: ([], []))
    def structured(*a, **kw):
        prompts.append(a[3])
        return result.model_copy(deep=True)
    monkeypatch.setattr(heimdall, "structured", structured)
    def run():
        with run_ctx("tenant", run_id="run"):
            return heimdall.map_event.__wrapped__({"event_id": "evt-test"})
    return event, result, saved, prompts, tools, run


def test_explicit_contract_update_is_not_discarded_for_having_no_breach(mapping):
    event, result, saved, prompts, tools, run = mapping
    event["contract_ids"] = ["C01"]
    out = run()
    assert out["contract_ids"] == ["C01"] and not out.get("noise")
    assert saved[-1][0][1] == "processed"
    assert saved[-1][1]["impact_review_required"] is True
    assert "requires review" in saved[-1][1]["effect"]
    assert not any(name in ("create_violation", "post_webhook") for name, _ in tools)


def test_subject_and_original_body_recover_a_reference_lost_by_parsing(mapping):
    event, result, saved, prompts, tools, run = mapping
    event["subject"] = "Payment for c01"
    event["raw"] = "Receipt INV-123; full supporting message"
    assert run()["contract_ids"] == ["C01"]
    assert "full supporting message" in prompts[0] and "Payment for c01" in prompts[0]
    assert "Known contract metadata" in prompts[0]


def test_unrelated_message_stays_noise(mapping):
    event, result, saved, prompts, tools, run = mapping
    assert run() == {"noise": True}
    assert saved[-1][0][1] == "noise"
    assert tools == []


def test_no_searchable_evidence_is_unresolved_not_proof_of_no_impact(mapping, monkeypatch):
    event, result, saved, prompts, tools, run = mapping
    monkeypatch.setattr(evidence, "retrieve", lambda *a, **kw: ([], ["No indexed clauses"]))
    out = run()
    assert out.get("errors") and not out.get("noise")
    assert saved[-1][0][1] == "needs_review"
    assert tools == []


def test_confirmed_payment_can_have_relevant_effect_without_violation(mapping):
    event, result, saved, prompts, tools, run = mapping
    event["contract_ids"] = ["C01"]
    result.is_noise = False
    result.effect = "Payment receipt needs reconciliation with the invoice."
    out = run()
    assert not out.get("noise") and not out["violation_ids"]
    assert saved[-1][1]["effect"] == result.effect


def test_contract_id_prefix_does_not_match_different_agreement(mapping):
    event, result, saved, prompts, tools, run = mapping
    event["subject"] = "C010 unrelated id"
    assert run().get("noise") is True


def test_incomplete_assessment_is_needs_review_not_processed_or_no_impact(monkeypatch):
    from types import SimpleNamespace
    from odin.graphs import event
    changes = []
    monkeypatch.setattr(event, "build", lambda: SimpleNamespace(invoke=lambda *a, **kw: {"errors": ["Provider unavailable"]}))
    monkeypatch.setattr(event.runs, "graph_config", lambda *a, **kw: {})
    monkeypatch.setattr(event.runs, "start", lambda company, kind, fn, **kw: fn("r"))
    monkeypatch.setattr(event.repo, "set_status", lambda *a, **kw: changes.append((a, kw)))
    assert event.run("tenant", "event", background=False) == "partial"
    assert changes[0][0] == ("event", "needs_review")
    assert "Provider unavailable" in changes[0][1]["reject_reason"]
