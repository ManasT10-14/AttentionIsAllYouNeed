"""Synthetic report persistence and provenance regressions; no model or database calls."""
from copy import deepcopy
from types import SimpleNamespace
from datetime import date
import pytest
from odin.agents import synth
from odin.core.context import run_ctx
from odin.core.budget import BudgetExceeded
from odin.services import message_results


@pytest.fixture
def store(monkeypatch):
    saved = {}
    monkeypatch.setattr(synth.repo, "get", lambda kind, rid: deepcopy(saved.get(rid)))
    def put(kind, model, **kw):
        data = model.model_dump(mode="json")
        saved[kw.get("rid") or data["id"]] = deepcopy(data)
        return data
    monkeypatch.setattr(synth.repo, "put", put)
    monkeypatch.setattr(synth.repo, "query", lambda *a, **kw: [])
    monkeypatch.setattr(synth.repo, "contract", lambda cid: SimpleNamespace(title=cid, current_version=1))
    monkeypatch.setattr(synth.repo, "contracts", lambda: [SimpleNamespace(contract_id="C1", current_version=1), SimpleNamespace(contract_id="C2", current_version=1)])
    monkeypatch.setattr(synth.repo, "sim_now", lambda: date(2026, 10, 26))
    monkeypatch.setattr(synth.insights, "extraction", lambda cid: None)
    monkeypatch.setattr(synth.insights, "timelines", lambda: [])
    monkeypatch.setattr(synth.insights, "health", lambda cid: {"score": 50})
    monkeypatch.setattr(synth.insights, "exposure_summary", lambda: {"expected": 10, "worst_case": 20, "currency": "INR"})
    monkeypatch.setattr(synth.insights, "prioritized_actions", lambda: [])
    monkeypatch.setattr(synth.insights, "counterparties", lambda: [])
    return saved


def test_budget_failure_keeps_contract_and_company_reports(store, monkeypatch):
    def fail(*a, **kw):
        assert store  # evidence must already be persisted before model work
        raise BudgetExceeded("test budget")
    monkeypatch.setattr(synth, "structured", fail)
    monkeypatch.setattr(synth, "say", lambda *a, **kw: None)
    with run_ctx("tenant", run_id="run-1"):
        rep = synth._write_contract("C1", {"status": "done"})
        synth._company({}, [rep], {})
    assert store["report:C1"]["summary_status"] == "unavailable"
    assert store["report:company"]["run_id"] == "run-1"
    assert set(store["report:company"]["workstreams"]) == {"C1", "C2", "cross"}
    assert store["report:company"]["summary_status"] == "unavailable"


def test_missing_reports_rebuilt_without_model_calls_and_preserve_existing_summary(store, monkeypatch):
    monkeypatch.setattr(synth, "structured", lambda *a, **kw: pytest.fail("recovery must not call a model"))
    with run_ctx("tenant"):
        original = synth._write_contract("C1", {"status": "done"}, generate_summary=False)
        original["summary"] = {"executive_summary": "Saved Synth summary"}
        store[original["id"]] = deepcopy(original)
        synth.rebuild_saved_reports(missing_only=True)
    assert store["report:C1"]["summary"]["executive_summary"] == "Saved Synth summary"
    assert "report:C2" in store
    assert "not a historical" in store["report:company"]["recovery_note"]


def test_contribution_is_a_snapshot_of_report_not_metadata(store):
    with run_ctx("tenant", run_id="run-1"):
        rep = synth._write_contract("C1", {"status": "done"}, generate_summary=False)
        result = message_results.capture_result("synth", "report", "C1", {"result_snapshot": deepcopy(rep)})
    assert result["source"] == "message_time_snapshot"
    assert result["report_id"] == "report:C1"
    assert any(s["title"] == "Executive summary" for s in result["sections"])
    store["report:C1"]["summary"] = {"executive_summary": "Changed"}
    assert result["sections"][0]["value"]["executive_summary"] != "Changed"


def test_verification_includes_rationale_even_without_contract_column(monkeypatch):
    monkeypatch.setattr(message_results.repo, "query", lambda kind, **kw: [{"id": "v", "rationale": "Clause supports the claim"}] if kind == "verification" else [])
    with run_ctx("tenant", run_id="r"):
        result = message_results.capture_result("heimdall", "verify", None, {})
    assert result["sections"][0]["value"][0]["rationale"] == "Clause supports the claim"


@pytest.mark.parametrize("scenario,expected", [(None, 1), ("preview", 0)])
def test_real_events_refresh_reports_but_simulations_do_not(monkeypatch, scenario, expected):
    from odin.graphs import event
    calls = []
    monkeypatch.setattr(event, "build", lambda: SimpleNamespace(invoke=lambda *a, **kw: {"contract_ids": ["C1"]}))
    monkeypatch.setattr(event.runs, "graph_config", lambda *a, **kw: {})
    monkeypatch.setattr(event.runs, "start", lambda company, kind, fn, **kw: fn("r"))
    monkeypatch.setattr(event.synth, "synthesize", lambda state: calls.append(state))
    assert event.run("tenant", "event", scenario_id=scenario, background=False) == "done"
    assert len(calls) == expected
    if calls:
        assert calls[0]["contract_ids"] == ["C1"]


def test_historical_snapshot_does_not_follow_later_changes(store, monkeypatch):
    from contextlib import contextmanager
    from odin.services import runs
    snapshots = []
    @contextmanager
    def fake_db():
        yield SimpleNamespace(add=lambda row: snapshots.append(deepcopy(row.data)))
    monkeypatch.setattr(runs, "db", fake_db)
    monkeypatch.setattr(runs, "run_reports", lambda company: [])
    monkeypatch.setattr(runs, "current_state", lambda: {"findings": {}, "actions": {}, "exposure": {"expected": 1, "worst_case": 2, "currency": "INR"}})
    with run_ctx("tenant", run_id="first"):
        report = synth._write_contract("C1", {"status": "done"}, generate_summary=False)
        store["report:company"] = {"id": "report:company", "run_id": "first", "completeness": "partial", "summary": {"executive_summary": "Original"}}
        monkeypatch.setattr(runs.repo, "query", lambda kind, **kw: [deepcopy(report)] if kind == "report" else [])
        runs.snapshot_report("tenant", "first", "event")
    store["report:company"]["summary"]["executive_summary"] = "Updated by later event"
    assert snapshots[0]["report"]["summary"]["executive_summary"] == "Original"
    assert snapshots[0]["contract_reports"][0]["contract_id"] == "C1"
    with run_ctx("tenant", run_id="second"):
        runs.snapshot_report("tenant", "second", "event")
    assert len(snapshots) == 1  # never attach another run's current report


def test_legacy_synth_message_never_substitutes_latest_report(monkeypatch):
    from contextlib import contextmanager
    from odin.api import workflow
    row = SimpleNamespace(company_id="tenant", payload={"completeness": "complete"}, sender="synth", kind="report", contract_id=None, run_id="first")
    @contextmanager
    def fake_db():
        yield SimpleNamespace(get=lambda *a: row)
    monkeypatch.setattr(workflow, "db", fake_db)
    def historical_only(kind, rid):
        assert kind == "report_run" and rid == "reportrun:first"
        return None
    monkeypatch.setattr(workflow.repo, "get", historical_only)
    result = workflow.message_result("message", SimpleNamespace(company_id="tenant", role="viewer"))
    assert result["source"] == "unavailable"
    assert result["sections"] == []


def test_each_upload_keeps_its_own_synth_output_after_latest_is_replaced(store):
    with run_ctx("tenant", run_id="upload-1"):
        synth._write_contract("C1", {"status": "done"}, generate_summary=False)
    with run_ctx("tenant", run_id="upload-2"):
        synth._write_contract("C1", {"status": "partial"}, generate_summary=False)
    assert store["reportrevision:upload-1:C1"]["completeness"] == "done"
    assert store["reportrevision:upload-2:C1"]["completeness"] == "partial"
    assert store["report:C1"]["run_id"] == "upload-2"


def test_intermediate_run_recovers_only_its_saved_outputs():
    from odin.services.runs import recover_report_outputs
    first = {"kind": "contract", "contract_id": "C1", "run_id": "first", "generated_at": "2026-10-01"}
    later = {"kind": "contract", "contract_id": "C6", "run_id": "later"}
    result = recover_report_outputs("first", [first, later, first])
    assert len(result["contract_reports"]) == 1
    assert result["contract_reports"][0]["contract_id"] == "C1"
    assert result["report"]["summary_status"] == "unavailable"
    assert recover_report_outputs("missing", [first, later]) is None


def test_report_refresh_runs_analysis_when_extraction_is_missing(monkeypatch):
    from odin.api import routes
    from odin.graphs import analysis
    calls = []
    monkeypatch.setattr(routes.repo, "contract", lambda cid: SimpleNamespace(contract_id=cid))
    monkeypatch.setattr(routes.insights, "extraction", lambda cid: None)
    monkeypatch.setattr(analysis, "run", lambda company, **kw: calls.append(kw) or "new-analysis")
    result = routes.refresh_reports(SimpleNamespace(company_id="tenant", role="admin"), contract_id="C1")
    assert result["mode"] == "analysis"
    assert calls == [{"contract_ids": ["C1"]}]


def test_refresh_with_saved_extraction_retries_synthesis_and_keeps_scope(monkeypatch):
    from odin.api import routes
    from odin.services import runs
    calls = []
    monkeypatch.setattr(routes.repo, "contract", lambda cid: SimpleNamespace(contract_id=cid))
    monkeypatch.setattr(routes.insights, "extraction", lambda cid: object())
    monkeypatch.setattr(routes.repo, "get", lambda *a: {"completeness": "unknown"})
    monkeypatch.setattr(synth, "synthesize", lambda state: calls.append(state) or {})
    monkeypatch.setattr(runs, "start", lambda company, kind, fn: fn("new-report") or "new-report")
    routes.refresh_reports(SimpleNamespace(company_id="tenant", role="admin"), contract_id="C1")
    assert calls[0]["contract_ids"] == ["C1"]
    assert calls[0]["ws_results"][0]["status"] == "partial"


def test_counterparty_exposure_retains_currency(monkeypatch):
    from odin.services import insights
    monkeypatch.setattr(insights.repo, "sim_now", lambda: date(2026, 10, 26))
    monkeypatch.setattr(insights, "exposure_summary", lambda now: {"contracts": [
        {"contract_id": "C1", "currency": "INR", "worst_case": 123}]})
    monkeypatch.setattr(insights.repo, "contracts", lambda: [SimpleNamespace(contract_id="C1", meta={"parties": [{"name": "Party", "role": "provider"}]})])
    monkeypatch.setattr(insights.repo, "query", lambda *a, **kw: [])
    monkeypatch.setattr(insights, "events_for", lambda cid: [])
    profile = insights.counterparties()[0]
    assert profile["currency"] == "INR"
    assert profile["worst_case_by_currency"] == {"INR": 123}
