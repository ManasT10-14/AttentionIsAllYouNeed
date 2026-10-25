"""Optional LangSmith evaluation runs and feedback, without product decorators."""

import asyncio
import hashlib
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from time import monotonic
from uuid import UUID, uuid4

from .config import TracingConfig
from .models import CaseReport


class LangSmithObserver:
    """Only status/score/timing metadata leaves the evaluator, never raw product data.

    These are evaluator-side runs, not automatic remote graph traces. Publishing is
    post-execution and best-effort; the runner records upload failure separately.
    """

    def __init__(self, config: TracingConfig, *, client=None, client_factory=None):
        self.config = config
        self.client = client
        self.client_factory = client_factory

    async def publish(self, case_report: CaseReport, run_id: str) -> str | None:
        if not self.config.enabled:
            return None
        return await asyncio.to_thread(self._publish, case_report, run_id)

    def _publish(self, case_report, run_id):
        deadline = monotonic() + self.config.publish_timeout_s
        client = self.client
        owned_session = None
        if client is None:
            key = os.environ.get(self.config.api_key_env)
            if not key:
                raise ValueError("LangSmith API key environment variable is missing")
            factory = self.client_factory
            if factory is None:
                from langsmith import Client

                factory = Client
            import requests
            from urllib3.util import Retry

            owned_session = requests.Session()
            try:
                client = factory(
                    api_key=key,
                    api_url=self.config.endpoint,
                    auto_batch_tracing=False,
                    timeout_ms=min(2000, max(1, int(self.config.publish_timeout_s * 1000))),
                    hide_inputs=True,
                    hide_outputs=True,
                    session=owned_session,
                    retry_config=Retry(
                        total=0,
                        connect=0,
                        read=0,
                        status=0,
                        redirect=0,
                        other=0,
                        respect_retry_after_header=False,
                    ),
                )
            except BaseException:
                owned_session.close()
                raise
        try:
            return self._publish_with_client(client, case_report, run_id, deadline)
        finally:
            if owned_session:
                owned_session.close()

    def _publish_with_client(self, client, case_report, run_id, deadline):
        def sdk_call(method, *args, **kwargs):
            # Cooperative budget plus bounded per-request timeouts and zero retries.
            # This does not abandon a background thread that asyncio.run must await.
            if monotonic() >= deadline:
                raise TimeoutError("LangSmith publishing budget exhausted")
            return method(*args, **kwargs)

        trace_id = str(uuid4())
        ended = datetime.now(timezone.utc)
        started = ended - timedelta(milliseconds=case_report.execution.latency_ms)
        case_hash = hashlib.sha256(case_report.case_id.encode()).hexdigest()
        product_trace = None
        try:
            product_trace = str(UUID(case_report.execution.trace_id))
        except (ValueError, TypeError, AttributeError):
            pass
        sdk_call(
            client.create_run,
            name="ragnarok.case",
            inputs={},
            run_type="chain",
            id=trace_id,
            project_name=self.config.project,
            start_time=started,
            extra={
                "metadata": {
                    "evaluation_run_id": run_id,
                    "case_id_sha256": case_hash,
                    "kind": case_report.kind,
                    "product_trace_id": product_trace,
                }
            },
        )
        counts = dict(Counter(check.status for check in case_report.checks))
        summary = {
            "check_status_counts": counts,
            "latency_ms": case_report.execution.latency_ms,
            "execution_state": case_report.execution.state,
        }
        sdk_call(
            client.update_run,
            trace_id,
            end_time=ended,
            outputs=summary,
            extra={
                "metadata": {
                    "evaluation_run_id": run_id,
                    "case_id_sha256": case_hash,
                    "kind": case_report.kind,
                    "product_trace_id": product_trace,
                    **summary,
                }
            },
        )
        for index, check in enumerate(case_report.checks):
            # Key labels contain no user-authored case/metric names or judge text.
            kwargs = {
                "key": f"check_{index}_{check.category}",
                "value": check.status,
                "comment": f"method={check.method}; required={check.required}",
            }
            if check.score is not None:
                kwargs["score"] = check.score
            sdk_call(client.create_feedback, run_id=trace_id, stop_after_attempt=1, **kwargs)
        return trace_id
