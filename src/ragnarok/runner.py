"""Small async orchestrator: execution, independent checks, optional observation."""

import asyncio
import hashlib
import importlib.metadata
import json
import math
import os
import time
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timezone
from uuid import uuid4

from .adapters import Adapter
from .checks import evaluate_check, result_for
from .config import RunConfig
from .judges import JUDGE_METRICS, DeepEvalEvaluator
from .models import CaseReport, CheckResult, Dataset, ExecutionResult, RunReport, SecurityCase
from .observability import LangSmithObserver
from .reporting import STATUSES, exit_code


def _hash(model):
    return hashlib.sha256(
        json.dumps(model.model_dump(mode="json"), sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def _versions():
    result = {}
    for package in ("ragnarok-eval", "pydantic", "httpx", "deepeval", "langsmith", "langgraph"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = "not installed"
    return result


def _secrets(config, dataset):
    values = []
    names = {"OPENAI_API_KEY", config.tracing.api_key_env}
    if config.http and config.http.auth_env:
        names.add(config.http.auth_env)
    names.update(
        name
        for name in os.environ
        if any(marker in name.upper() for marker in ("API_KEY", "PASSWORD", "SECRET", "TOKEN"))
    )
    values.extend(os.environ[name] for name in names if os.environ.get(name))
    for case in dataset.cases:
        for check in case.checks:
            if check.name == "no_secret" and isinstance(check.params.get("canaries"), list):
                values.extend(item for item in check.params["canaries"] if isinstance(item, str))
    return values


def _usage(cases):
    usages = [case.execution.usage for case in cases]
    result = {"usage_cases": sum(usage is not None for usage in usages)}
    for name in ("input_tokens", "output_tokens"):
        known = [
            getattr(usage, name)
            for usage in usages
            if usage is not None and getattr(usage, name) is not None
        ]
        result[name] = sum(known) if known and len(known) == len(cases) else None
        result["known_" + name] = sum(known) if known else None
    costs = Counter()
    cost_cases = 0
    for usage in usages:
        if usage and usage.cost is not None and usage.currency:
            costs[usage.currency] += usage.cost
            cost_cases += 1
    result.update(cost_by_currency=dict(costs), cost_cases=cost_cases)
    return result


async def run(
    config: RunConfig, dataset: Dataset, adapter: Adapter, *, observer=None, judge_evaluator=None
) -> RunReport:
    run_id = str(uuid4())
    observer = observer or LangSmithObserver(config.tracing)
    judge = judge_evaluator or DeepEvalEvaluator(config.judge)
    semaphore = asyncio.Semaphore(config.concurrency)

    async def one(case):
        async with semaphore:
            if (
                isinstance(case, SecurityCase)
                and case.security.side_effecting
                and not config.allow_side_effects
            ):
                return CaseReport(
                    case_id=case.id,
                    kind=case.kind,
                    execution=ExecutionResult(state="partial"),
                    checks=[
                        CheckResult(
                            name="safety_gate",
                            status="skipped",
                            required=True,
                            reason="Side-effecting security case requires allow_side_effects=true",
                            category="security",
                            severity=case.security.severity,
                        )
                    ],
                )
            started = time.perf_counter()
            checks = []
            if not case.checks:
                execution = ExecutionResult(state="partial")
                checks.append(
                    CheckResult(
                        name="selection",
                        status="skipped",
                        required=True,
                        reason="No checks configured",
                        category=case.kind,
                    )
                )
            elif not any(spec.enabled for spec in case.checks):
                execution = ExecutionResult(state="partial")
                checks.extend(
                    result_for(spec, case, "skipped", "Check disabled") for spec in case.checks
                )
            else:
                try:
                    execution = await asyncio.wait_for(
                        adapter.execute(case, f"{run_id}:{case.id}"), timeout=config.case_timeout_s
                    )
                    if not isinstance(execution, ExecutionResult):
                        raise TypeError("Adapter must return ExecutionResult")
                except Exception as exc:
                    message = (
                        "Adapter timed out"
                        if isinstance(exc, TimeoutError)
                        else (f"Adapter execution failed ({type(exc).__name__})")
                    )
                    execution = ExecutionResult(state="error", errors=[message])
                execution.latency_ms = (time.perf_counter() - started) * 1000
                if execution.state == "error":
                    checks.append(
                        CheckResult(
                            name="execution",
                            status="error",
                            required=True,
                            reason="Target execution failed; inspect adapter configuration or product logs",
                            category=case.kind,
                        )
                    )
                else:
                    for spec in case.checks:
                        try:
                            if spec.name in JUDGE_METRICS:
                                check = await judge.evaluate(spec, case, execution)
                            else:
                                check = evaluate_check(spec, case, execution)
                        except Exception as exc:
                            check = result_for(
                                spec, case, "error", f"Evaluator failed ({type(exc).__name__})"
                            )
                        checks.append(check)
                    if isinstance(case, SecurityCase):
                        missing = []
                        for field in case.security.required_evidence:
                            value = getattr(execution, field)
                            if field in {"output", "usage"}:
                                available = value is not None
                            else:
                                available = value.state == "complete"
                            if not available:
                                missing.append(field)
                        if missing:
                            checks.append(
                                CheckResult(
                                    name="required_evidence",
                                    status="skipped",
                                    required=True,
                                    category="security",
                                    severity=case.security.severity,
                                    reason="Declared complete evidence missing: "
                                    + ", ".join(missing),
                                )
                            )
                    if execution.state == "partial":
                        checks.append(
                            CheckResult(
                                name="execution_complete",
                                status="skipped",
                                required=True,
                                reason="Target reported incomplete execution",
                                category=case.kind,
                            )
                        )
            report = CaseReport(case_id=case.id, kind=case.kind, execution=execution, checks=checks)
            try:
                report.observer_trace_id = await observer.publish(report, run_id)
            except Exception as exc:
                report.observer_warning = f"LangSmith publishing unavailable ({type(exc).__name__})"
            return report

    # Product graph imports may inherit ambient tracing settings from the shell.
    # Automatic in-process uploads are suppressed; the explicit observer owns uploads.
    try:
        from langsmith import tracing_context

        tracing_guard = tracing_context(enabled=False)
    except ImportError:
        tracing_guard = nullcontext()
    selected = [
        case
        for case in dataset.cases
        if case.enabled and (not config.include_tags or set(config.include_tags) & set(case.tags))
    ]
    with tracing_guard:
        cases = await asyncio.gather(*(one(case) for case in selected))
    counter = Counter(check.status for case in cases for check in case.checks)
    measured = sorted(case.execution.latency_ms for case in cases if case.execution.latency_ms > 0)
    findings = [
        {
            "case_id": case.case_id,
            "check": check.name,
            "severity": check.severity,
            "reason": check.reason,
        }
        for case in cases
        for check in case.checks
        if check.category == "security" and check.status == "failed"
    ]
    report = RunReport(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc),
        dataset_id=dataset.id,
        dataset_sha256=_hash(dataset),
        config_sha256=_hash(config),
        adapter=config.adapter,
        synthetic=dataset.synthetic,
        package_versions=_versions(),
        cases=cases,
        counts={status: counter[status] for status in STATUSES},
        security_findings=findings,
        latency={
            "mean_ms": sum(measured) / len(measured) if measured else None,
            "p95_ms": measured[math.ceil(0.95 * len(measured)) - 1] if measured else None,
        },
        usage=_usage(cases),
        exit_code=exit_code(cases),
    )
    report._redaction_values = _secrets(config, dataset)
    return report
