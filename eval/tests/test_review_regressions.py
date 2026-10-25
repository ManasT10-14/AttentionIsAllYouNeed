import asyncio
from unittest.mock import MagicMock, Mock, patch

import pytest

from ragnarok.checks import evaluate_check
from ragnarok.config import TracingConfig
from ragnarok.models import CaseReport, CheckResult, CheckSpec, EvaluationCase, ExecutionResult
from ragnarok.observability import LangSmithObserver


@pytest.mark.parametrize("canary", ['synthetic"canary', r"synthetic\canary", "synthetic\ncanary"])
def test_literal_disclosure_cannot_hide_behind_json_escaping(canary):
    result = evaluate_check(
        CheckSpec(name="no_secret", params={"canaries": [canary]}),
        EvaluationCase(id="c", input="q"),
        ExecutionResult(output=canary),
    )
    assert result.status == "failed"


@pytest.mark.parametrize(
    "actual,expected", [(1, True), (0, False), ({"approved": [1]}, {"approved": [True]}), (1.0, 1)]
)
def test_exact_json_comparison_preserves_types(actual, expected):
    result = evaluate_check(
        CheckSpec(name="exact_match"),
        EvaluationCase(id="c", input="q", expected_output=expected),
        ExecutionResult(output=actual),
    )
    assert result.status == "failed"


def test_tool_argument_boolean_is_not_a_number():
    result = evaluate_check(
        CheckSpec(name="tool_arguments", params={"expected": {"send": {"approved": False}}}),
        EvaluationCase(id="c", input="q"),
        ExecutionResult(
            tools={
                "state": "complete",
                "items": [{"name": "send", "phase": "executed", "arguments": {"approved": 0}}],
            }
        ),
    )
    assert result.status == "failed"


def _report():
    return CaseReport(
        case_id="c",
        kind="quality",
        execution=ExecutionResult(output="a"),
        checks=[CheckResult(name="exact_match", status="passed", reason="ok")],
    )


def test_feedback_rate_limit_does_not_retry():
    import requests
    from langsmith import Client
    from langsmith.utils import LangSmithRateLimitError

    session = requests.Session()

    def respond(method, url, **kwargs):
        response = requests.Response()
        response.status_code = 429 if url.endswith("/feedback") else 200
        response._content = b"{}"
        response.url = url
        response.headers["retry-after"] = "30"
        return response

    session.request = Mock(side_effect=respond)
    client = Client(
        api_url="http://offline.invalid",
        api_key="synthetic-placeholder",
        auto_batch_tracing=False,
        info={},
        session=session,
        timeout_ms=2000,
    )
    observer = LangSmithObserver(TracingConfig(enabled=True), client=client)
    try:
        with (
            patch("langsmith.client.time.sleep") as sleep,
            patch("langsmith.client.random.random", return_value=0),
        ):
            with pytest.raises(LangSmithRateLimitError):
                asyncio.run(observer.publish(_report(), "00000000-0000-0000-0000-000000000001"))
            feedback_calls = [
                call
                for call in session.request.call_args_list
                if call.args[1].endswith("/feedback")
            ]
            assert len(feedback_calls) == 1
            sleep.assert_not_called()
    finally:
        session.close()


def test_owned_langsmith_client_disables_transport_retries(monkeypatch):
    monkeypatch.setenv("TEST_LANGSMITH_KEY", "synthetic-placeholder")
    factory = MagicMock(return_value=MagicMock())
    observer = LangSmithObserver(
        TracingConfig(enabled=True, api_key_env="TEST_LANGSMITH_KEY"), client_factory=factory
    )
    asyncio.run(observer.publish(_report(), "r"))
    retry = factory.call_args.kwargs["retry_config"]
    assert retry.total == 0
    assert not retry.respect_retry_after_header


def test_publishing_budget_stops_between_sdk_calls():
    client = MagicMock()
    observer = LangSmithObserver(TracingConfig(enabled=True), client=client)
    with patch("ragnarok.observability.monotonic", side_effect=[0, 0, 11]):
        with pytest.raises(TimeoutError):
            asyncio.run(observer.publish(_report(), "r"))
    client.create_run.assert_called_once()
    client.update_run.assert_not_called()


def test_safe_summary_is_available_as_metadata_when_outputs_are_hidden():
    client = MagicMock()
    observer = LangSmithObserver(TracingConfig(enabled=True), client=client)
    asyncio.run(observer.publish(_report(), "r"))
    metadata = client.update_run.call_args.kwargs["extra"]["metadata"]
    assert metadata["check_status_counts"] == {"passed": 1}
    assert metadata["execution_state"] == "complete"
