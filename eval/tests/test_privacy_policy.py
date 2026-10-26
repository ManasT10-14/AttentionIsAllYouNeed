"""Report export privacy uses synthetic values and in-memory reports only."""
import json
from datetime import UTC, datetime

from ragnarok.models import RunReport
from ragnarok.reporting import redact, write_report


def test_report_export_redacts_nested_sensitive_keys_and_environment_literals(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_TEST_TOKEN", "syntheticOpaqueEnvironmentLiteral")
    payload = {"nested": [{"clientSecret": "tiny", "password_hint": "arbitrary-value", "cookie": "session-opaque"}],
               "diagnostic": "syntheticOpaqueEnvironmentLiteral", "contact": "notice@example.test"}
    report = RunReport(run_id="privacy-test", dataset_id="synthetic", timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                       dataset_sha256="synthetic", config_sha256="synthetic", adapter="synthetic", synthetic=True,
                       package_versions={}, cases=[], counts={}, latency={}, usage=payload, exit_code=0)
    path = tmp_path / "report.json"
    write_report(report, path)
    result = path.read_text(encoding="utf-8")
    for secret in ("tiny", "arbitrary-value", "session-opaque", "syntheticOpaqueEnvironmentLiteral"):
        assert secret not in result
    assert "notice@example.test" in result
    assert report.usage == payload
    assert json.loads(result)["usage"]["nested"][0]["cookie"] == "[REDACTED]"


def test_report_redaction_preserves_explicit_canary_and_pii_evidence_policy():
    value = {"output": "SYNTHETIC_CASE_CANARY", "evidence": "4111 1111 1111 1111", "api_key": "x"}
    result = redact(value, secrets=["synthetic_case_canary"])
    assert result["output"] == "[REDACTED]"
    assert result["api_key"] == "[REDACTED]"
    assert result["evidence"] == value["evidence"]
