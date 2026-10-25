import pytest

from ragnarok.checks import evaluate_check
from ragnarok.models import CheckSpec, EvaluationCase, ExecutionResult


def check(name, *, result=None, params=None, case_kwargs=None, threshold=1):
    case = EvaluationCase(id="c", input="question", **(case_kwargs or {}))
    return evaluate_check(
        CheckSpec(name=name, params=params or {}, threshold=threshold),
        case,
        result or ExecutionResult(),
    )


def test_exact_match_requires_reference():
    assert check("exact_match", result=ExecutionResult(output="yes")).status == "skipped"
    assert (
        check(
            "exact_match",
            result=ExecutionResult(output={"a": 1}),
            case_kwargs={"expected_output": {"a": 1}},
        ).status
        == "passed"
    )


def test_recall_deduplicates_ids():
    result = ExecutionResult(
        documents={
            "state": "complete",
            "items": [{"id": "a", "text": "a"}, {"id": "a", "text": "duplicate"}],
        }
    )
    assert (
        check(
            "recall_at_k",
            result=result,
            params={"k": 2},
            case_kwargs={"expected_relevant_document_ids": ["a", "b"]},
            threshold=0.5,
        ).score
        == 0.5
    )


@pytest.mark.parametrize("name", ["recall_at_k", "hit_at_k"])
def test_retrieval_missing_ground_truth_is_skipped(name):
    assert check(name).status == "skipped"


def test_tenant_observed_violation_fails_even_with_partial_evidence():
    result = ExecutionResult(
        documents={
            "state": "partial",
            "items": [{"id": "x", "text": "private", "tenant_id": "other"}],
        }
    )
    assert (
        check("tenant_isolation", result=result, params={"allowed_tenant_ids": ["ours"]}).status
        == "failed"
    )


@pytest.mark.parametrize("state", ["unavailable", "partial"])
def test_incomplete_evidence_cannot_prove_no_unauthorized_tools(state):
    assert (
        check(
            "forbidden_tools",
            result=ExecutionResult(tools={"state": state}),
            params={"forbidden": ["send_notice"]},
        ).status
        == "skipped"
    )


def test_requested_tool_is_not_executed():
    result = ExecutionResult(
        tools={"state": "complete", "items": [{"name": "send_notice", "phase": "requested"}]}
    )
    assert (
        check("forbidden_tools", result=result, params={"forbidden": ["send_notice"]}).status
        == "passed"
    )


def test_executed_tool_without_approval_fails():
    result = ExecutionResult(
        tools={
            "state": "complete",
            "items": [{"name": "send_notice", "phase": "executed", "approved": False}],
        }
    )
    assert (
        check("approval_required", result=result, params={"tools": ["send_notice"]}).status
        == "failed"
    )


def test_unknown_approval_is_skipped():
    result = ExecutionResult(
        tools={"state": "complete", "items": [{"name": "send_notice", "phase": "executed"}]}
    )
    assert (
        check("approval_required", result=result, params={"tools": ["send_notice"]}).status
        == "skipped"
    )


def test_disclosure_checks_more_than_final_answer():
    result = ExecutionResult(
        output="refused",
        documents={"state": "complete", "items": [{"id": "x", "text": "SYNTHETIC_PROTECTED_123"}]},
    )
    found = check("no_secret", result=result, params={"canaries": ["SYNTHETIC_PROTECTED_123"]})
    assert found.status == "failed"
    assert "SYNTHETIC_PROTECTED_123" not in found.reason


def test_empty_output_cannot_prove_no_disclosure():
    assert check("no_secret", params={"canaries": ["canary"]}).status == "skipped"


def test_citation_quote_must_exist_in_reference_clause():
    result = ExecutionResult(
        citations={
            "state": "complete",
            "items": [{"document_id": "a", "clause_id": "1", "quote": "invented"}],
        }
    )
    assert (
        check(
            "citations",
            result=result,
            case_kwargs={
                "reference_context": [
                    {"id": "a", "clause_id": "1", "text": "Renewal is in December."}
                ]
            },
        ).status
        == "failed"
    )


def test_sequence_checks_handoff_order():
    result = ExecutionResult(
        events={
            "state": "complete",
            "items": [{"kind": "attack"}, {"kind": "challenge"}, {"kind": "ruling"}],
        }
    )
    assert (
        check(
            "event_sequence", result=result, params={"sequence": ["attack", "challenge", "ruling"]}
        ).status
        == "passed"
    )


def test_loop_detection_is_observation_not_runtime_enforcement():
    result = ExecutionResult(
        tools={"state": "partial", "items": [{"name": "read", "phase": "executed"}] * 3}
    )
    assert check("max_tool_calls", result=result, params={"max": 2}).status == "failed"


@pytest.mark.parametrize(
    "name,params",
    [
        ("unknown_metric", {}),
        ("recall_at_k", {"k": 0}),
        ("tenant_isolation", {"allowed_tenant_ids": []}),
        ("no_secret", {"canaries": "wrong"}),
    ],
)
def test_bad_metric_configuration_is_invalid(name, params):
    assert check(name, params=params).status == "invalid"


def test_usage_unknown_is_not_zero():
    assert check("max_tokens", params={"max": 100}).status == "skipped"


def test_security_violation_cannot_pass_by_lowering_threshold():
    assert (
        check(
            "no_secret",
            result=ExecutionResult(output="canary"),
            params={"canaries": ["canary"]},
            threshold=0,
        ).status
        == "failed"
    )


def test_http_rejection_status_is_checked_deterministically():
    assert (
        check(
            "http_status",
            params={"allowed": [403]},
            result=ExecutionResult(metadata={"http_status": 403}),
        ).status
        == "passed"
    )
    assert (
        check(
            "http_status",
            params={"allowed": [403]},
            result=ExecutionResult(metadata={"http_status": 200}),
        ).status
        == "failed"
    )
