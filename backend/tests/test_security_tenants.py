"""Tenant and role regressions use synthetic SQLite data, never the app database."""
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from odin.api import auth, pack, quality, routes, security_status, workflow
from odin.api.deps import current_user
from odin.core.context import run_ctx
from odin.db import repo
from odin.db.tables import Base, Company, Contract, ContractVersion, Record, Run
from odin.services import runs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def workspace(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def db():
        with factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    for module in (repo, routes, workflow, quality, pack, runs, security_status, auth):
        monkeypatch.setattr(module, "db", db)
    with db() as session:
        session.add_all([Company(id="A"), Company(id="B")])
        for company in ("B", "A"):
            session.add(Record(id=f"{company}|r", company_id=company, kind="event", scenario_id="shared",
                               data={"id": "r", "status": "processed", "owner_label": company}))
            session.add(Run(id=f"run-{company}", company_id=company, kind="whatif", scenario_id="shared", status="done"))
        session.add(Record(id="B|foreign", company_id="B", kind="event", scenario_id="only-B", data={"id": "foreign"}))
        session.add(Run(id="foreign-run", company_id="B", kind="whatif", scenario_id="only-B"))
        session.add(Contract(id="B-contract", company_id="B", contract_id="B-only"))
        session.add(ContractVersion(id="B-version", company_id="B", contract_id="B-only", version=1,
                                    sha256="b"*64, text="private B terms", file_path="private", pdf_path="private"))
        session.add(Record(id="B|eval-job", company_id="B", kind="eval_suite", data={"id": "eval-job"}))
        session.add(Record(id="B|incident", company_id="B", kind="security_event", data={"id": "incident"}))
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    app.include_router(workflow.router, prefix="/api")
    app.include_router(quality.router, prefix="/api")
    app.include_router(pack.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    user = SimpleNamespace(id="user-A", email="admin@a.test", company_id="A", role="admin")
    app.dependency_overrides[current_user] = lambda: user
    user.name, user.gmail_address = "Fixture admin", None
    monkeypatch.setattr(auth, "current_user", lambda request: user)
    monkeypatch.setattr(routes.insights, "exposure_summary", lambda: {})
    from odin.core import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    # Provider/intake/scheduling effects are outside this role test's boundary.
    monkeypatch.setattr(routes.events_svc, "receive", lambda *a, **kw: {"status": "test-only"})
    return SimpleNamespace(db=db, client=TestClient(app), user=user)


def test_foreign_and_unknown_scenarios_are_indistinguishable(workspace):
    foreign = workspace.client.get("/api/whatif/only-B")
    unknown = workspace.client.get("/api/whatif/missing")
    assert foreign.status_code == unknown.status_code == 404
    assert foreign.json() == unknown.json()


def test_shared_scenario_reads_only_owned_run(workspace):
    result = workspace.client.get("/api/whatif/shared")
    assert result.status_code == 200
    assert result.json()["run"]["id"] == "run-A"
    assert result.json()["records"]["event"][0]["owner_label"] == "A"


def test_scenario_delete_preserves_other_tenant_and_checks_ownership(workspace):
    assert workspace.client.delete("/api/whatif/only-B").status_code == 404
    assert workspace.client.delete("/api/whatif/shared").status_code == 200
    with workspace.db() as session:
        assert session.get(Record, "B|r") is not None
        assert session.get(Record, "B|foreign") is not None
        assert session.get(Record, "A|r") is None
        assert session.get(Run, "run-B") is not None


def test_repository_rejects_missing_or_overridden_tenant(workspace):
    with pytest.raises(RuntimeError):
        repo.query("event")
    with pytest.raises(RuntimeError):
        repo.drop_scenario("shared")
    with run_ctx("A"):
        with pytest.raises(PermissionError):
            repo.query("event", company_id="B")
        with pytest.raises(PermissionError):
            repo.contract("B-only", company_id="B")
        repo.update_run("foreign-run", status="done")
    with workspace.db() as session:
        assert session.get(Run, "foreign-run").status == "running"


@pytest.mark.parametrize("path", ["/contracts/B-only", "/contracts/B-only/versions/1/pdf",
    "/contracts/B-only/versions/1/original", "/runs/foreign-run", "/workflow/foreign-run",
    "/reports/events/foreign", "/reports/runs/foreign-run", "/evals/suite/eval-job"])
def test_foreign_object_routes_deny_access(workspace, path):
    assert workspace.client.get("/api" + path).status_code == 404


def test_foreign_security_review_does_not_modify_incident(workspace):
    result = workspace.client.post("/api/security/events/incident", json={"decision": "dismiss", "note": "Reviewed"})
    assert result.status_code == 404
    with workspace.db() as session:
        assert session.get(Record, "B|incident").data == {"id": "incident"}


@pytest.mark.parametrize("path,payload", [
    ("/events", {"subject": "Test", "body": "Test"}),
    ("/email/poll-now", {}), ("/whatif", {"subject": "Test", "body": "Test"}),
    ("/reports/refresh", {}), ("/owners", {"timeline_id": "x", "owner": "me"}),
    ("/demo/play", {}), ("/alerts/x", {"status": "resolved"}),
    ("/simulation/step", {}), ("/bundle/import", {}),
])
def test_viewer_cannot_invoke_state_changes(workspace, path, payload):
    workspace.user.role = "viewer"
    assert workspace.client.post("/api" + path, json=payload).status_code == 403


def test_public_event_json_masks_arbitrary_credentials(workspace):
    with workspace.db() as session:
        session.add(Record(id="A|public", company_id="A", kind="event", data={"id": "public",
            "raw": "password: SyntheticPrivateValue41", "details": {"access_token": "ArbitraryFixtureToken42"}}))
    response = workspace.client.get("/api/events")
    assert response.status_code == 200
    assert "SyntheticPrivateValue41" not in response.text
    assert "ArbitraryFixtureToken42" not in response.text


def test_auth_company_context_response_uses_privacy_policy(workspace):
    with workspace.db() as session:
        session.get(Company, "A").context = {"raw_text": "password: SyntheticContextSecret41",
                                            "access_token": "ArbitraryContextToken42"}
    response = workspace.client.get("/api/auth/me")
    assert response.status_code == 200
    assert "SyntheticContextSecret41" not in response.text
    assert "ArbitraryContextToken42" not in response.text


def test_generated_exports_mask_credentials(workspace, monkeypatch):
    monkeypatch.setattr(routes.insights, "actions_csv", lambda: "body\npassword: SyntheticExportSecret41")
    response = workspace.client.get("/api/export/actions.csv")
    assert response.status_code == 200
    assert "SyntheticExportSecret41" not in response.text


def test_validation_errors_do_not_echo_credentials(workspace):
    response = workspace.client.post("/api/ask", json={"question": {"password": "SyntheticValidationSecret45"}})
    assert response.status_code == 422
    assert "SyntheticValidationSecret45" not in response.text


def test_http_error_does_not_echo_secret_bearing_reference(workspace):
    response = workspace.client.get("/api/citation/resolve", params={"contract": "password: SyntheticQuerySecret46", "clause": "3"})
    assert response.status_code == 404
    assert "SyntheticQuerySecret46" not in response.text


def test_scenario_export_never_includes_private_evidence(workspace):
    with workspace.db() as session:
        session.add(Record(id="A|quarantine:r", company_id="A", kind="quarantine_evidence", scenario_id="shared",
                           data={"id": "quarantine:r", "body": "PrivateCanonicalEvidence47"}))
    workspace.user.role = "viewer"
    response = workspace.client.get("/api/whatif/shared")
    assert response.status_code == 200
    assert "quarantine_evidence" not in response.json()["records"]
    assert "PrivateCanonicalEvidence47" not in response.text


def test_workspace_reset_cannot_remove_executing_approval(workspace):
    with workspace.db() as session:
        session.add(Record(id="A|executing-action", company_id="A", kind="action", status="approved",
                           data={"id": "executing-action", "status": "approved", "approval_execution": {"state": "executing"}}))
    response = workspace.client.post("/api/workspace/reset")
    assert response.status_code == 409
    with workspace.db() as session:
        assert session.get(Record, "A|executing-action") is not None


def test_admin_evidence_preview_can_resolve_owned_scenario(workspace):
    with workspace.db() as session:
        session.add(Record(id="A|incident-scenario", company_id="A", kind="security_event",
                           data={"id": "incident-scenario", "event_id": "r"}))
        session.add(Record(id="A|quarantine:r", company_id="A", kind="quarantine_evidence", scenario_id="shared",
                           data={"id": "quarantine:r", "evidence": {"body": "Reviewable source password: PrivateReviewSecret49"}}))
    response = workspace.client.get("/api/security/events/incident-scenario/evidence")
    assert response.status_code == 200
    assert response.json()["canonical_evidence_available"] is True
    assert "Reviewable source" in response.text
    assert "PrivateReviewSecret49" not in response.text
    workspace.user.role = "viewer"
    assert workspace.client.get("/api/security/events/incident-scenario/evidence").status_code == 403


def test_run_failure_masks_diagnostics_before_storage_and_logging(workspace, monkeypatch, caplog):
    from odin.core.hooks import HOOKS
    monkeypatch.setattr(HOOKS, "evals", [])
    def fail(_):
        raise ValueError("password: SyntheticRunSecret50")
    rid = runs.start("A", "security_probe", fail, background=False)
    with workspace.db() as session:
        row = session.get(Run, rid)
        assert row.status == "failed"
        assert "SyntheticRunSecret50" not in row.error
        assert "ValueError" in row.error
    assert "SyntheticRunSecret50" not in caplog.text


def test_rejected_release_cannot_be_reprocessed_outside_review(workspace):
    with workspace.db() as session:
        session.add(Record(id="A|failed-release", company_id="A", kind="event", status="needs_review",
                           data={"id": "failed-release", "status": "needs_review", "review_release_status": "release_failed"}))
    assert workspace.client.post("/api/events/failed-release/reprocess").status_code == 409


def test_sse_publication_masks_credentials_before_queue(monkeypatch):
    from odin.core import bus
    monkeypatch.setattr(bus, "_loop", SimpleNamespace(call_soon_threadsafe=lambda fn, msg: fn(msg)))
    queue = bus.subscribe("security-fixture")
    try:
        bus.publish("security-fixture", "event", {"password": "PrivateArbitraryValue47"})
        assert "PrivateArbitraryValue47" not in queue.get_nowait()
    finally:
        bus.unsubscribe("security-fixture", queue)


def test_html_report_export_masks_credentials_before_render():
    response = workflow._respond({"body": "password: SyntheticHtmlSecret48"},
                                 lambda r: "<p>" + r["body"] + "</p>", "synthetic", "html")
    assert b"SyntheticHtmlSecret48" not in response.body


def test_security_status_never_calls_unconfigured_guard_protected(workspace, monkeypatch):
    from odin.core.hooks import HOOKS
    monkeypatch.setattr(HOOKS, "guards", [])
    result = workspace.client.get("/api/security/status")
    assert result.status_code == 200
    assert result.json()["guard_enabled"] is False
    assert result.json()["trace_privacy_mode"] == "metadata_only"
    assert result.json()["limitations"]
    assert all(x["status"] != "enforced" for x in result.json()["protected_surfaces"] if x["name"] == "model_inputs")
