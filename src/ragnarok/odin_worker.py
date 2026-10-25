"""Private subprocess entrypoint: one execution, no golden labels, no API server/poller."""

import contextlib
import json
import sys
from uuid import uuid4

from .config import OdinConfig
from .models import ExecutionResult
from .odin_capture import EvaluationGuard, capture, normalize


def execute(config: OdinConfig, question, request_id: str):
    from odin.core import budget
    from odin.core.config import settings
    from odin.core.context import run_ctx
    from odin.core.hooks import HOOKS
    from odin.core.telemetry import span

    settings()
    HOOKS.guards.append(EvaluationGuard(allow_internal_writes=config.disposable_database))
    run_id = str(uuid4())
    parameters = dict(config.parameters)
    trace_id = None
    try:
        with capture(max_records=config.max_records) as observed:
            with run_ctx(config.company_id, run_id=run_id):
                with span(f"odin-eval:{config.operation}") as trace:
                    trace_id = str(trace.id) if trace else None
                    if config.operation in {"ask", "retrieval"}:
                        if not isinstance(question, str) or not question.strip():
                            raise ValueError("Odin query input must be nonempty text")
                        if config.operation == "ask":
                            from odin.services.ask import ask

                            output = ask(config.company_id, question, **parameters)
                        else:
                            from odin.retrieval.hybrid import search

                            output = [hit.as_dict(None) for hit in search(question, **parameters)]
                    elif config.operation == "tool_probe":
                        import odin.tools.core  # noqa: F401
                        from odin.tools.registry import REGISTRY

                        if not isinstance(question, dict) or set(question) - {
                            "agent",
                            "tool",
                            "arguments",
                        }:
                            raise ValueError("tool_probe accepts agent, tool, arguments only")
                        try:
                            REGISTRY.invoke(
                                question["agent"], question["tool"], question.get("arguments", {})
                            )
                            output = {"denied": False}
                        except Exception as exc:
                            output = {"denied": True, "error_type": type(exc).__name__}
                    else:
                        output = graph(config, run_id)
        result = normalize(observed, output, operation=config.operation)
        result.trace_id = trace_id
        result.metadata.update(product_run_id=run_id, request_id=request_id)
        # Fake LLMs can verify wiring but can never claim golden evaluation success.
        if "fake" in result.metadata["providers"] and not config.allow_fake_provider:
            result.state = "error"
            result.errors.append(
                "Fake provider rejected; configure a real model or explicitly allow smoke mode"
            )
        return result
    finally:
        budget.release(run_id)
        # execute() is also usable from Python tests; leave no global policy behind.
        HOOKS.guards[:] = [
            guard for guard in HOOKS.guards if not isinstance(guard, EvaluationGuard)
        ]


def graph(config, run_id):
    from odin.db import repo
    from odin.services.runs import graph_config, new_run

    new_run(config.company_id, config.operation, run_id=run_id)
    state = {"company_id": config.company_id, "run_id": run_id, **config.parameters}
    if config.operation == "analysis":
        from odin.graphs.analysis import build

        state.setdefault("contract_ids", [])
    elif config.operation == "event":
        from odin.graphs.event import build

        state.update(debate_round=0, finding_ids=[])
    else:
        from odin.graphs.update import build
    out = build().invoke(state, config=graph_config(run_id, config.operation))
    artifacts = {
        kind: repo.query(kind, run_id=run_id)
        for kind in (
            "extraction",
            "finding",
            "verification",
            "ruling",
            "action",
            "alert",
            "violation",
            "report",
        )
    }
    repo.update_run(run_id, status=out.get("final_status", "partial"))
    return {**out, "artifacts": artifacts}


def main():
    # Reserve stdout for exactly one machine-readable envelope. Product libraries
    # sometimes print; move those messages to stderr (discarded by the adapter).
    payload = json.load(sys.stdin)
    try:
        with contextlib.redirect_stdout(sys.stderr):
            result = execute(
                OdinConfig.model_validate(payload["config"]),
                payload["input"],
                payload["request_id"],
            )
    except Exception as exc:
        result = ExecutionResult(
            state="error", errors=[f"Odin execution failed ({type(exc).__name__})"]
        )
    sys.stdout.buffer.write(result.model_dump_json().encode("utf-8"))
    try:
        from odin.core.telemetry import client, enabled

        if enabled():
            client().flush()
    except Exception:
        pass


if __name__ == "__main__":
    main()
