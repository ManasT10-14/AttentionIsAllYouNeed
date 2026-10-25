"""Optional DeepEval integration; no provider construction until explicitly enabled."""

import asyncio
import math
import os
from collections.abc import Callable

from .checks import MissingEvidence, result_for
from .config import JudgeConfig
from .models import CheckResult, CheckSpec, EvaluationCase, ExecutionResult

JUDGE_METRICS = {
    "faithfulness": "FaithfulnessMetric",
    "answer_relevancy": "AnswerRelevancyMetric",
    "contextual_relevancy": "ContextualRelevancyMetric",
    "contextual_precision": "ContextualPrecisionMetric",
    "contextual_recall": "ContextualRecallMetric",
}


def build_metric(name: str, threshold: float, model):
    # Opt out of library telemetry; optional LangSmith uploads are separately configured.
    os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
    from deepeval import metrics

    return getattr(metrics, JUDGE_METRICS[name])(
        threshold=threshold, model=model, include_reason=True, verbose_mode=False
    )


class DeepEvalEvaluator:
    def __init__(self, config: JudgeConfig, *, metric_factory: Callable | None = None):
        self.config = config
        self.metric_factory = metric_factory or build_metric

    async def evaluate(
        self, spec: CheckSpec, case: EvaluationCase, execution: ExecutionResult
    ) -> CheckResult:
        def result(status, reason, score=None):
            return result_for(spec, case, status, reason, score, method="llm_judge")

        if not spec.enabled or not self.config.enabled:
            return result("skipped", "Check disabled" if not spec.enabled else "LLM judge disabled")
        if spec.name not in JUDGE_METRICS:
            return result("invalid", "Unknown DeepEval metric")
        if spec.params:
            return result(
                "invalid", "DeepEval checks accept threshold; no metric params are supported"
            )
        try:
            if not isinstance(case.input, str) or not case.input.strip():
                raise MissingEvidence(
                    "DeepEval requires a nonempty text input; configure an input mapping"
                )
            data = {"input": case.input}
            if spec.name in {"faithfulness", "answer_relevancy"}:
                if not isinstance(execution.output, str) or not execution.output.strip():
                    raise MissingEvidence(
                        "This metric requires a nonempty text output; configure an output mapping"
                    )
                data["actual_output"] = execution.output
            if spec.name != "answer_relevancy":
                context = (
                    execution.model_context
                    if execution.model_context.state != "unavailable"
                    else execution.documents
                )
                if context.state != "complete" or not context.items:
                    raise MissingEvidence("Complete, nonempty actual retrieval context is required")
                data["retrieval_context"] = (
                    list(context.items)
                    if context is execution.model_context
                    else [doc.text for doc in context.items]
                )
            if spec.name in {"contextual_precision", "contextual_recall"}:
                if not isinstance(case.expected_output, str) or not case.expected_output.strip():
                    raise MissingEvidence("A nonempty reference answer is required")
                data["expected_output"] = case.expected_output
            os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
            from deepeval.test_case import LLMTestCase

            test_case = LLMTestCase(**data)
            # A new instance per evaluation avoids mutable score/reason races across cases.
            metric = self.metric_factory(spec.name, spec.threshold, self.config.model)
            await asyncio.wait_for(metric.a_measure(test_case), timeout=self.config.timeout_s)
            score = float(metric.score)
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("Judge returned a score outside [0, 1]")
            return result(
                "passed" if score >= spec.threshold else "failed",
                metric.reason or "Judge returned no explanation",
                score,
            )
        except MissingEvidence as exc:
            return result("skipped", str(exc))
        except ImportError:
            return result("error", "Install the judge extra to run DeepEval metrics")
        except TimeoutError:
            return result("error", "LLM judge timed out")
        except Exception as exc:
            # Provider errors can contain credentials or request bodies.
            return result("error", f"DeepEval evaluation failed ({type(exc).__name__})")
