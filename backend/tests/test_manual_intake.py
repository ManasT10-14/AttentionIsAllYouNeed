"""Manual intake must expose parser rejection as an HTTP failure to keep the form open."""
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from odin.api import routes
from odin.api.deps import current_user


@pytest.mark.parametrize("status,code", [("rejected", 422), ("accepted", 200), ("duplicate", 200)])
def test_manual_intake_http_status(monkeypatch, status, code):
    result = {"status": status, "event_id": "evt-test", "problems": ["OCCURRED_AT is missing"]}
    monkeypatch.setattr(routes.events_svc, "receive", lambda *a, **kw: result)
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(company_id="test", role="admin")
    with TestClient(app) as client:
        response = client.post("/api/events", json={"subject": "Test", "body": "???"})
    assert response.status_code == code
    if status == "rejected":
        assert response.json()["detail"] == "OCCURRED_AT is missing"
    else:
        assert response.json()["event_id"] == "evt-test"


def test_retrying_rejected_manual_event_keeps_validation_error(monkeypatch):
    import hashlib
    from odin.services import events
    subject, body = "Test", "???"
    dedupe = hashlib.sha1(f"{subject}\n{body}".encode()).hexdigest()[:16]
    monkeypatch.setattr(events.repo, "query", lambda kind: [{
        "id": "evt-rejected", "gmail_msg_id": dedupe,
        "status": "rejected", "reject_reason": "OCCURRED_AT is missing",
    }])
    result = events.receive("test", subject=subject, body=body, method="manual", run=False)
    assert result["status"] == "rejected"
    assert result["event_id"] == "evt-rejected"
    assert result["problems"] == ["OCCURRED_AT is missing"]
