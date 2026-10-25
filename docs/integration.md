# Connecting the real product

Odin's actual services and graphs are now connected. See
[Odin integration](odin-integration.md) for the scoped-hook/subprocess adapter,
product traces and golden configs. The generic HTTP and graph adapter notes
below remain useful for other targets.

## HTTP: default integration

Start the fixture application to exercise HTTP locally:

```powershell
uv run --all-extras uvicorn --app-dir eval examples.mock_product:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
uv run --all-extras ragnarok run --config eval/configs/http.example.json
```

This is a real FastAPI application serving recorded synthetic results, not a model-powered Odin implementation. The automated HTTP integration test uses HTTPX's ASGI transport; it exercises routing/serialization without a TCP server.

Change `http.base_url`, `endpoint`, `method`, `input_field`, `payload`, and `response_mapping` for the actual backend. Paths inside a config resolve relative to that config file. `input_field` is a single top-level JSON key, `payload` supplies static siblings, and `response_mapping` uses dotted keys/list indexes. Arbitrary transformations or multipart uploads need a custom adapter; no executable mapping expressions are evaluated. Dataset inputs may be JSON objects.

For example, with a backend taking `{"question": "..."}` and returning `{"result": {"answer": "...", "chunks": [...]}}`:

```json
{
  "base_url": "http://127.0.0.1:8000",
  "endpoint": "/analyze",
  "input_field": "question",
  "response_mapping": {
    "output": "result.answer",
    "documents": "result.chunks"
  },
  "auth_env": "ODIN_API_TOKEN"
}
```

Export the token in your shell. The default header is `Authorization: Bearer ...`; customize `auth_header` and `auth_prefix` if necessary. Each request includes `X-Request-ID`. Redirects are refused, the endpoint must share the base URL's origin, and URL credentials are rejected. No product request is automatically retried.

Requests use a JSON body for the configured method. Query-string input and async job polling are not implemented. A 202/job response is not a complete result: provide a custom polling adapter or wait for backend details. `case_timeout_s` bounds adapter execution; it does not prove remote work stopped. `http.timeout_s` controls HTTPX's transport timeouts. Judge calls have a separate timeout; there is no total run deadline.

By default a non-2xx response is an execution error. Set `allow_error_responses` to true for security cases evaluating expected rejection responses, then add `http_status` with `allowed: [401, 403]` or the appropriate codes. In that mode response status is exposed in `execution.metadata.http_status`; missing output on a rejected response is allowed. Add independent checks for authorization/side effects when required: a 403 alone does not establish that an operation was never executed.

## Evidence format

Every optional collection uses:

```json
{
  "state": "complete",
  "items": [{"id": "contract-a", "text": "Clause text", "tenant_id": "alpha", "clause_id": "2.1"}]
}
```

`unavailable` means no evidence was exposed; `partial` means only some records were observed. A plain list in an HTTP mapping is shorthand for a complete collection. **Only use that shorthand if the backend guarantees completeness.** Otherwise return the explicit envelope. Missing optional mapping paths stay unavailable; malformed mapped data is an adapter error.

Other record shapes:

```json
{
  "tools": {"state": "complete", "items": [
    {"name": "read_clause", "arguments": {"id": "a"}, "phase": "executed", "authorized": true, "approved": true}
  ]},
  "events": {"state": "complete", "items": [
    {"kind": "clarification", "actor": "reviewer", "target": "extractor"}
  ]},
  "citations": {"state": "complete", "items": [
    {"document_id": "contract-a", "clause_id": "2.1", "quote": "Clause text"}
  ]},
  "usage": {"input_tokens": 100, "output_tokens": 20, "cost": 0.001, "currency": "USD"},
  "state": "complete",
  "output": "Final answer",
  "trace_id": null
}
```

Possible tool phases: requested, authorized, attempted, executed, failed. Requested/authorized events alone do not establish execution. Map one attempted/executed/failed record per call for count metrics; multiple lifecycle records for one call would otherwise be counted separately. Audit completeness and labels must come from trustworthy instrumentation, not from an LLM's narrative assertion. This evaluator does not independently authenticate those records.

Reference clauses/answers belong to the dataset and are never substituted for actual retrieval. For semantic DeepEval checks, normalize question/output to strings; the text of actual retrieved documents supplies `retrieval_context`. Structured report scoring needs a product-specific text/field mapping or a new evaluator.

## In-process LangGraph alternative

```python
import asyncio
from ragnarok.adapters import GraphAdapter
from ragnarok.config import RunConfig
from ragnarok.datasets import load_dataset
from ragnarok.models import ExecutionResult
from ragnarok.reporting import write_report
from ragnarok.runner import run

# graph is the real compiled graph, constructed by your product integration code.
adapter = GraphAdapter(
    graph,
    input_mapper=lambda case: {"query": case.input},  # replace with actual state mapping
    output_mapper=lambda state: ExecutionResult(output=state["answer"]),
    graph_config={"recursion_limit": 20},
)
report = asyncio.run(run(RunConfig(adapter="graph"), load_dataset("my-cases.json"), adapter))
write_report(report, "reports/graph.json")
```

The example `query`/`answer` keys are placeholders chosen by the caller. The adapter knows no node names or state fields and invokes `ainvoke` once. Populate optional evidence in `output_mapper` if the graph exposes it. Recursion limits count LangGraph supersteps, not exact tool calls or token budgets. Runtime limits and real authorization remain product responsibilities. The runner suppresses ambient SDK tracing; product span instrumentation can be added explicitly when ready.

## Adding cases and evaluators

A normal case contains `kind` (quality or agent), ID, JSON input, optional expected output, source clauses, relevance labels, tags, and `checks`. Each check has name, enabled, required, threshold, and params. Configuration rejects unknown model fields. Case IDs and check names within a case must be unique.

A security case uses `kind: security` and an additional `security` object specifying attack category, invariant, severity, required evidence, evaluation method (currently deterministic), and optional side-effecting flag. Required evidence fields must be completely available even when the final answer looks safe. Observed violations still fail with partial evidence. `side_effecting: true` blocks execution unless `allow_side_effects` is explicitly enabled; never use production secrets or real destructive tools.

Add deterministic behavior in `checks.py` with a failing test, then expose it through `evaluate_check`. Add a supported judge to the registry/validation in `judges.py` only after checking exact DeepEval inputs. Keep real network tests separate from the offline suite. Application-specific deadline arithmetic, total financial exposure, event-to-clause mapping and UI tests await the backend schema and labelled ground truth.

## Observability limits

LangSmith feedback is published using the SDK client API, without `@traceable`. Remote feedback currently uses stable index/category keys; the local report gives metric names and explanations. Optional uploads happen after evaluation; they do not create live nested product spans. Trace-upload failures are best-effort warnings, so CI requiring observability should separately gate on `observer_warning`. Remote product trace IDs, when exposed, remain separate from evaluator observer IDs.
