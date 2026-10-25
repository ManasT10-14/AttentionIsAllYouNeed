import asyncio
from unittest.mock import MagicMock

import pytest

from ragnarok.config import JudgeConfig, TracingConfig
from ragnarok.judges import DeepEvalEvaluator
from ragnarok.models import CaseReport, CheckResult, CheckSpec, EvaluationCase, ExecutionResult
from ragnarok.observability import LangSmithObserver


def test_judge_disabled_never_constructs_a_metric():
    factory = MagicMock()
    evaluator = DeepEvalEvaluator(JudgeConfig(), metric_factory=factory)
    result = asyncio.run(
        evaluator.evaluate(
            CheckSpec(name="faithfulness"),
            EvaluationCase(id="c", input="q"),
            ExecutionResult(output="a"),
        )
    )
    assert result.status == "skipped"
    factory.assert_not_called()


def test_reference_context_is_not_actual_retrieval():
    factory = MagicMock()
    evaluator = DeepEvalEvaluator(JudgeConfig(enabled=True), metric_factory=factory)
    case = EvaluationCase(id="c", input="q", reference_context=[{"id": "r", "text": "reference"}])
    result = asyncio.run(
        evaluator.evaluate(CheckSpec(name="faithfulness"), case, ExecutionResult(output="a"))
    )
    assert result.status == "skipped"
    factory.assert_not_called()


def test_judge_inputs_score_and_fresh_metric_per_call():
    metrics = []

    def factory(name, threshold, model):
        class Metric:
            score = 0.8
            reason = "Supported claims"

            async def a_measure(self, test_case):
                assert test_case.retrieval_context == ["actual evidence"]
                assert test_case.input == "q"
                assert test_case.actual_output == "a"

        metric = Metric()
        metrics.append(metric)
        assert name == "faithfulness" and threshold == 0.7 and model == "test-judge"
        return metric

    evaluator = DeepEvalEvaluator(
        JudgeConfig(enabled=True, model="test-judge"), metric_factory=factory
    )
    case = EvaluationCase(id="c", input="q")
    execution = ExecutionResult(
        output="a",
        documents={"state": "complete", "items": [{"id": "x", "text": "actual evidence"}]},
    )
    for _ in range(2):
        result = asyncio.run(
            evaluator.evaluate(CheckSpec(name="faithfulness", threshold=0.7), case, execution)
        )
        assert result.status == "passed" and result.method == "llm_judge"
        assert result.score == 0.8
    assert metrics[0] is not metrics[1]


def test_judge_timeout_is_error():
    class Slow:
        async def a_measure(self, test_case):
            await asyncio.sleep(0.1)

    evaluator = DeepEvalEvaluator(
        JudgeConfig(enabled=True, timeout_s=0.01), metric_factory=lambda *args: Slow()
    )
    result = asyncio.run(
        evaluator.evaluate(
            CheckSpec(name="answer_relevancy"),
            EvaluationCase(id="c", input="q"),
            ExecutionResult(output="a"),
        )
    )
    assert result.status == "error"


def test_contextual_recall_requires_reference_answer():
    evaluator = DeepEvalEvaluator(JudgeConfig(enabled=True), metric_factory=MagicMock())
    result = asyncio.run(
        evaluator.evaluate(
            CheckSpec(name="contextual_recall"),
            EvaluationCase(id="c", input="q"),
            ExecutionResult(
                output="a",
                documents={"state": "complete", "items": [{"id": "x", "text": "context"}]},
            ),
        )
    )
    assert result.status == "skipped"


def test_retrieval_judge_does_not_require_an_actual_answer():
    class Metric:
        score = 1.0
        reason = "Relevant context"

        async def a_measure(self, test_case):
            assert test_case.actual_output is None
            assert test_case.retrieval_context == ["context"]

    evaluator = DeepEvalEvaluator(JudgeConfig(enabled=True), metric_factory=lambda *args: Metric())
    result = asyncio.run(
        evaluator.evaluate(
            CheckSpec(name="contextual_relevancy"),
            EvaluationCase(id="c", input="q"),
            ExecutionResult(
                documents={"state": "complete", "items": [{"id": "x", "text": "context"}]}
            ),
        )
    )
    assert result.status == "passed"


def report():
    return CaseReport(
        case_id="sensitive-case-name",
        kind="quality",
        execution=ExecutionResult(output="PRIVATE OUTPUT", latency_ms=12),
        checks=[
            CheckResult(
                name="faithfulness",
                status="passed",
                score=0.9,
                reason="PRIVATE REASON",
                method="llm_judge",
            )
        ],
    )


def test_tracing_off_never_constructs_a_client():
    factory = MagicMock()
    observer = LangSmithObserver(TracingConfig(), client_factory=factory)
    assert asyncio.run(observer.publish(report(), "run-one")) is None
    factory.assert_not_called()


def test_tracing_uploads_only_safe_metadata_and_feedback():
    client = MagicMock()
    observer = LangSmithObserver(TracingConfig(enabled=True), client=client)
    trace_id = asyncio.run(observer.publish(report(), "run-one"))
    assert trace_id
    assert client.create_run.call_count == client.update_run.call_count == 1
    assert client.create_feedback.call_args.kwargs["score"] == 0.9
    transmitted = str(client.mock_calls)
    for private in ["PRIVATE OUTPUT", "PRIVATE REASON", "sensitive-case-name"]:
        assert private not in transmitted


def test_sdk_failure_propagates_for_runner_to_record():
    client = MagicMock()
    client.create_run.side_effect = RuntimeError("DO NOT LOG THIS")
    observer = LangSmithObserver(TracingConfig(enabled=True), client=client)
    with pytest.raises(RuntimeError):
        asyncio.run(observer.publish(report(), "run-one"))


def test_real_deepeval_metrics_construct_without_provider_calls(monkeypatch):
    monkeypatch.setenv("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
    from deepeval.models import DeepEvalBaseLLM

    class OfflineJudge(DeepEvalBaseLLM):
        def load_model(self):
            return self

        def generate(self, *args, **kwargs):
            raise AssertionError("No live judge invocation expected")

        async def a_generate(self, *args, **kwargs):
            raise AssertionError("No live judge invocation expected")

        def get_model_name(self):
            return "offline-construction-only"

    from ragnarok.judges import JUDGE_METRICS, build_metric

    for name in JUDGE_METRICS:
        metric = build_metric(name, 0.7, OfflineJudge())
        assert metric.threshold == 0.7
        assert callable(metric.a_measure)


def test_actual_deepeval_measurement_with_offline_custom_model():
    """Exercise real DeepEval async orchestration, not semantic model quality."""
    from deepeval.models import DeepEvalBaseLLM

    from ragnarok.judges import build_metric

    class SchemaJudge(DeepEvalBaseLLM):
        def load_model(self):
            return self

        def generate(self, *args, **kwargs):
            raise AssertionError("The async path must be used")

        async def a_generate(self, prompt, schema=None, **kwargs):
            fields = schema.model_fields
            if "statements" in fields:
                return schema(statements=["30 days notice is required."])
            if "verdicts" in fields:
                return schema.model_validate({"verdicts": [{"verdict": "yes"}]})
            if "reason" in fields:
                return schema(reason="The statement addresses the notice question.")
            raise AssertionError("Unexpected judge schema")

        def get_model_name(self):
            return "offline-schema-fixture"

    evaluator = DeepEvalEvaluator(
        JudgeConfig(enabled=True),
        metric_factory=lambda name, threshold, model: build_metric(name, threshold, SchemaJudge()),
    )
    result = asyncio.run(
        evaluator.evaluate(
            CheckSpec(name="answer_relevancy", threshold=0.7),
            EvaluationCase(id="c", input="What notice is required?"),
            ExecutionResult(output="30 days notice is required."),
        )
    )
    assert result.status == "passed" and result.score == 1
