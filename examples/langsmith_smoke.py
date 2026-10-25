"""Upload only synthetic status metadata and verify both trace trees and feedback.

Run: uv run --env-file .env --all-extras python examples/langsmith_smoke.py
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from ragnarok.config import TracingConfig
from ragnarok.models import CaseReport, CheckResult, ExecutionResult
from ragnarok.observability import LangSmithObserver


def main():
    logging.disable(logging.CRITICAL)
    from odin.core.telemetry import client, span

    product_id = str(uuid4())
    with span("odin:synthetic-integration-smoke", run_id=product_id) as root:
        if root is None:
            print("LangSmith product tracing is not configured")
            return 2
        with span("odin:synthetic-retrieval", "retriever"):
            pass
    client().flush()
    report = CaseReport(
        case_id="synthetic-connection-check",
        kind="quality",
        execution=ExecutionResult(output="synthetic", trace_id=product_id),
        checks=[
            CheckResult(
                name="synthetic_wiring",
                status="passed",
                score=1,
                reason="Synthetic transport check only",
            )
        ],
    )
    evaluation_id = asyncio.run(
        LangSmithObserver(TracingConfig(enabled=True)).publish(report, str(uuid4()))
    )
    # Ingestion is eventually consistent. Bounded reads, no model invocations.
    for attempt in range(5):
        try:
            product = client().read_run(product_id)
            evaluation = client().read_run(evaluation_id)
            feedback = list(client().list_feedback(run_ids=[evaluation_id], limit=5))
            children = list(
                client().list_runs(project_name="ragnarok-odin", trace_id=product_id, limit=5)
            )
            if feedback and len(children) >= 2:
                assert product.inputs in (None, {}) and product.outputs in (None, {})
                assert evaluation.inputs in (None, {}) and evaluation.outputs in (None, {})
                print(
                    json.dumps(
                        {
                            "verified": True,
                            "product_trace_url": client().get_run_url(run=product),
                            "evaluation_trace_url": client().get_run_url(run=evaluation),
                            "feedback_count": len(feedback),
                            "product_spans": len(children),
                        }
                    )
                )
                return 0
        except Exception:
            if attempt == 4:
                raise
        time.sleep(2)
    print("LangSmith ingestion could not be verified within the read budget")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"LangSmith verification failed ({type(exc).__name__}); no credentials printed")
        raise SystemExit(2)
