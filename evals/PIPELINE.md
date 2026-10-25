# Ragnarok

Evaluation and security infrastructure connected to the Odin backend in `backend/`.
It runs actual RAG services and agent graphs through an isolated worker,
scores observations with deterministic checks and optional DeepEval metrics, and
publishes private product traces plus evaluation feedback to LangSmith.

See [Odin integration and golden dataset setup](docs/odin-integration.md).

The offline suite exercises real services with synthetic data. LangSmith uploads,
span readback and feedback were verified with synthetic metadata. Real provider
answers, PostgreSQL/pgvector retrieval and golden accuracy await live data/setup.

## Run locally

Python 3.11 and [uv](https://docs.astral.sh/uv/) are used. A project-local environment and `uv.lock` keep evaluator dependencies separate from the product.

```powershell
uv sync --all-extras
uv run --all-extras pytest -q
uv run --all-extras ragnarok validate datasets/odin/synthetic.json
uv run --all-extras ragnarok run --config configs/offline.json
```

The last command writes `reports/offline.json` and exits 0. Five paid metrics are explicitly skipped; deterministic checks still run. To demonstrate detected violations:

```powershell
uv run --all-extras ragnarok run --config configs/vulnerable.json
```

This deliberately exits 1 and writes `reports/vulnerable.json`. It includes fabricated citations, an incorrect answer, tenant leakage, protected canary disclosure, forbidden notice execution, missing approval, excessive activity, and improper acceptance of malformed input. All data and tool events are synthetic; no notice is actually sent.

For a smaller installation, `uv sync` installs the core and development dependencies. Add `--extra judge`, `--extra tracing`, or `--extra graph` as needed. The full test suite requires all extras but does not require credentials or paid calls. Tests block external socket connections; Windows asyncio loopback sockets are allowed.

## What is implemented

- Async fixture, configurable HTTPX, and in-process compiled-graph adapters.
- Pydantic configuration/dataset/evidence schemas and actionable validation failures.
- Independent deterministic quality, agent and security checks.
- Five optional DeepEval metrics, with exact required-input validation and isolated judge instances/timeouts.
- Optional LangSmith evaluation runs and score/status feedback, without product `@traceable` decorators.
- Bounded concurrency, execution timeouts, failure isolation, explicit coverage gaps, and atomic redacted JSON reports.
- Synthetic Odin datasets, safe/vulnerable results, FastAPI fixture service, and actual compiled LangGraph smoke test.

## Enable DeepEval deliberately

```powershell
$env:OPENAI_API_KEY = "your-key"
uv run --all-extras ragnarok run --config configs/deepeval.json
```

This sends the synthetic RAG question, answer and required evidence to the configured judge and can incur provider charges. `gpt-4.1-mini` is an example model setting, not a requirement. Replace it with a supported model available to your account. No real provider call was made during development.

Judge scores are probabilistic. The sample 0.7 threshold is illustrative and must be calibrated. DeepEval is lazy-loaded, library telemetry is opted out by default, and each metric receives its own instance. The evaluator measures the metric's result; LangSmith does not automatically calculate these scores.

## Enable LangSmith deliberately

```powershell
$env:LANGSMITH_API_KEY = "your-key"
uv run --all-extras ragnarok run --config configs/langsmith.example.json
```

This publishes evaluator-side case runs with hashed case identifiers, run ID, kind, execution status, check counts, latency, and score/status feedback. Contract text, raw answers, secrets and judge reasons are excluded from remote payloads. Feedback keys use check indexes and categories; match their order to the JSON report. A returned observer trace ID links the case to its LangSmith run.

The generic observer publishes evaluation records. The Odin adapter additionally
creates private product spans when `odin.product_tracing=true`, and links them
through `product_trace_id` metadata. Automatic child exception text is sanitized.
Generic in-process ambient tracing remains suppressed by the runner. Upload
failures produce an `observer_warning` without changing check outcomes. Synthetic
account uploads, readback and feedback have been verified.

SDK/transport retries are disabled for publishing. A configurable `tracing.publish_timeout_s` budget (default 10 seconds) is checked between calls, with per-request SDK timeouts capped at two seconds. An in-flight request can exceed the remaining budget; custom injected clients must provide their own bounded transport. This prevents the SDK's default feedback retry/backoff from delaying evaluation for hours.

## Reports and CI

`counts` counts check results, not case results. `cases` contains the executions and each check; `security_findings` contains observed security failures separately. Results record dataset/configuration hashes, package versions, latency, exposed product usage and costs. Unknown usage remains null and costs stay grouped by currency. Product latency is measured at the adapter boundary; judge and publishing time are not part of that latency. Judge token/cost accounting is not yet collected.

| Status | Meaning |
|---|---|
| passed | The observed criterion was met |
| failed | An observed criterion was violated |
| error | Adapter/provider/evaluator failed or timed out |
| skipped | Disabled check or insufficient evidence |
| invalid | Unknown metric or invalid metric parameters |

Exit code precedence is 2 (error/invalid), 1 (failure), 3 (no passing assertion or required check skipped), then 0. An optional skipped judge does not fail an otherwise passing run. Disabling a required check does not silently satisfy it. Skips never count as passes.

Reports mask configured synthetic canaries, relevant environment credentials, common key patterns and sensitive named fields. **Reports still contain product outputs and documents and can include personal or commercially sensitive information.** Keep them local, review before sharing, and add domain-specific redaction before using real contracts. Use `write_report()` for persisted output: `model_dump()` returns unredacted in-memory observations by design. Credentials belong in environment variables; `.env.example` is only a reference and is not auto-loaded by Ragnarok.

## Odin backend integration

The actual backend is connected through the `odin` adapter. Follow
[the integration guide](docs/odin-integration.md) for RAG, retrieval, agent and
security configs and [the golden dataset contract](datasets/golden/README.md).

See [generic adapter instructions](docs/integration.md) and
[metric definitions](docs/metrics.md) for other targets. Odin calls its own hooks;
the independent worker supplies the Ragnarok collector. Missing telemetry is
reported explicitly. The original [architecture proposal](docs/architecture-proposal.md)
contains additional timeline, exposure and event-driven golden test ideas.
