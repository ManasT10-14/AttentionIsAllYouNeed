import asyncio
import json

import pytest

from ragnarok.adapters import FixtureAdapter
from ragnarok.config import RunConfig
from ragnarok.models import Dataset, ExecutionResult
from ragnarok.reporting import write_report
from ragnarok.runner import run


def dataset(*cases):
    return Dataset.model_validate(
        {
            "id": "synthetic",
            "cases": [
                {"kind": "quality", "input": "q", "id": f"c{i}", **case}
                for i, case in enumerate(cases)
            ],
        }
    )


def execute(data, fixtures=None, config=None, **kwargs):
    return asyncio.run(run(config or RunConfig(), data, FixtureAdapter(fixtures or {}), **kwargs))


def test_offline_success_and_report_round_trip(tmp_path):
    data = dataset({"expected_output": "yes", "checks": [{"name": "exact_match"}]})
    report = execute(data, {"c0": ExecutionResult(output="yes")})
    assert report.exit_code == 0
    assert report.counts["passed"] == 1
    path = tmp_path / "nested" / "report.json"
    write_report(report, path)
    raw = json.loads(path.read_text())
    assert raw["run_id"] == report.run_id and raw["schema_version"] == "1.0"
    assert raw["usage"]["input_tokens"] is None


@pytest.mark.parametrize(
    "check,expected",
    [
        ({"name": "exact_match"}, 3),
        ({"name": "exact_match", "enabled": False}, 3),
        ({"name": "unknown_check"}, 2),
    ],
)
def test_exit_codes_for_missing_disabled_and_invalid(check, expected):
    assert (
        execute(dataset({"checks": [check]}), {"c0": ExecutionResult(output="a")}).exit_code
        == expected
    )


def test_failure_exit_and_optional_skip():
    report = execute(
        dataset(
            {
                "expected_output": "right",
                "checks": [{"name": "exact_match"}, {"name": "faithfulness", "required": False}],
            }
        ),
        {"c0": ExecutionResult(output="wrong")},
    )
    assert report.exit_code == 1
    assert report.counts["failed"] == report.counts["skipped"] == 1


@pytest.mark.parametrize("data", [dataset(), dataset({"enabled": False}), dataset({})])
def test_empty_or_no_assertions_does_not_pass(data):
    assert execute(data, {"c0": ExecutionResult()}).exit_code == 3


def test_timeout_does_not_lose_other_cases():
    class Adapter:
        async def execute(self, case, request_id):
            if case.id == "c0":
                await asyncio.sleep(0.1)
            return ExecutionResult(output="yes")

    data = dataset(*[{"expected_output": "yes", "checks": [{"name": "exact_match"}]}] * 2)
    report = asyncio.run(run(RunConfig(case_timeout_s=0.01), data, Adapter()))
    assert report.exit_code == 2
    assert report.counts["passed"] == report.counts["error"] == 1
    assert len(report.cases) == 2


def test_execution_failure_cannot_pass_even_if_checks_are_optional():
    report = execute(dataset({"checks": [{"name": "exact_match", "required": False}]}))
    assert report.exit_code == 2


def test_partial_execution_is_not_marked_complete():
    report = execute(
        dataset({"expected_output": "a", "checks": [{"name": "exact_match"}]}),
        {"c0": ExecutionResult(output="a", state="partial")},
    )
    assert report.exit_code == 3


def test_observer_failure_does_not_change_evaluation():
    class Observer:
        async def publish(self, case_report, run_id):
            raise RuntimeError("secret-network-detail")

    report = execute(
        dataset({"expected_output": "a", "checks": [{"name": "exact_match"}]}),
        {"c0": ExecutionResult(output="a")},
        observer=Observer(),
    )
    assert report.exit_code == 0
    assert report.cases[0].observer_warning
    assert "secret-network-detail" not in report.model_dump_json()


def test_side_effecting_security_case_is_blocked_before_adapter():
    data = dataset(
        {
            "kind": "security",
            "security": {
                "attack_category": "tool",
                "invariant": "Do not send a notice",
                "side_effecting": True,
            },
            "checks": [{"name": "no_secret", "params": {"canaries": ["synthetic"]}}],
        }
    )

    class Adapter:
        async def execute(self, case, request_id):
            raise AssertionError("must not be called")

    report = asyncio.run(run(RunConfig(), data, Adapter()))
    assert report.exit_code == 3
    assert report.counts["skipped"] == 1


def test_concurrency_is_bounded():
    class Adapter:
        active = 0
        maximum = 0

        async def execute(self, case, request_id):
            self.active += 1
            self.maximum = max(self.maximum, self.active)
            await asyncio.sleep(0.01)
            self.active -= 1
            return ExecutionResult(output="a")

    adapter = Adapter()
    data = dataset(*[{"expected_output": "a", "checks": [{"name": "exact_match"}]}] * 5)
    report = asyncio.run(run(RunConfig(concurrency=2), data, adapter))
    assert report.exit_code == 0 and adapter.maximum == 2


def test_reports_redact_canaries_and_environment_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-private-api-key")
    data = dataset(
        {
            "kind": "security",
            "security": {
                "attack_category": "disclosure",
                "invariant": "Synthetic protected value stays hidden",
            },
            "checks": [{"name": "no_secret", "params": {"canaries": ["SYNTHETIC_CANARY_ABC"]}}],
        }
    )
    result = ExecutionResult(
        output="SYNTHETIC_CANARY_ABC synthetic-private-api-key",
        metadata={"authorization": "another-private-value"},
    )
    report = execute(data, {"c0": result})
    path = tmp_path / "report.json"
    write_report(report, path)
    text = path.read_text()
    for secret in ["SYNTHETIC_CANARY_ABC", "synthetic-private-api-key", "another-private-value"]:
        assert secret not in text
    assert report.exit_code == 1
    assert report.security_findings


def test_judge_exception_isolated_from_other_checks():
    class Judge:
        async def evaluate(self, *args):
            raise RuntimeError("private provider response")

    data = dataset(
        {"expected_output": "a", "checks": [{"name": "faithfulness"}, {"name": "exact_match"}]}
    )
    report = execute(data, {"c0": ExecutionResult(output="a")}, judge_evaluator=Judge())
    assert report.counts["error"] == report.counts["passed"] == 1
    assert "private provider response" not in report.model_dump_json()


def test_tags_filter_before_execution():
    data = dataset(
        {"tags": ["rag"], "checks": [{"name": "exact_match"}], "expected_output": "a"},
        {"tags": ["security"]},
    )
    report = execute(
        data, {"c0": ExecutionResult(output="a")}, config=RunConfig(include_tags=["rag"])
    )
    assert len(report.cases) == 1 and report.exit_code == 0


def test_security_declared_evidence_is_required_even_if_answer_looks_safe():
    data = dataset(
        {
            "kind": "security",
            "security": {
                "attack_category": "tool",
                "invariant": "No unauthorized operation",
                "required_evidence": ["tools"],
            },
            "checks": [{"name": "no_secret", "params": {"canaries": ["canary"]}}],
        }
    )
    report = execute(data, {"c0": ExecutionResult(output="Refused")})
    assert report.exit_code == 3
