# First integration notes (historical)

Current repository layout, golden setup and handoff are in [CHECKPOINT.md](CHECKPOINT.md).
The earlier parent-workspace layout described below has been consolidated into this repository.

The backend checkout is `backend/`, branch `feat/ragnarok-evaluation`, based on
`e550f874181ce992053dcc08f523b6842d37bd94`. The evaluator remains the installable
project at this workspace root. Keep both directories together. Nothing has been
pushed to GitHub.

## Setup

```powershell
uv sync --locked --all-extras
uv run --locked --all-extras pytest -q
uv run --locked --all-extras pytest backend/backend/tests -q
uv run --env-file .env --all-extras ragnarok run --config configs/odin.security.json
```

The supplied LangSmith credential is in ignored `.env` and `backend/.env` files.
Never copy them into datasets, reports or commits. Product settings read
`backend/.env`; `uv run --env-file .env` supplies the evaluator's environment.
Configure the disposable evaluation database and actual model provider in those
local files before live RAG/agent runs. Root optional `odin` dependencies include
the graph, tracing, provider SDKs, embeddings, SQL and parsing libraries needed by
the worker. The API/UI/Gmail server still uses the backend's own requirements.

The registry smoke config makes four synthetic denial probes. It writes audit
rows when a database is available, and does not initialize a database or start
the API, Gmail poller, or external tools. Probe outcomes do not prove resistance
to every prompt injection attack.

## Actual execution path

CLI -> OdinAdapter -> isolated Python worker -> product service/compiled graph
-> scoped hooks -> normalized ExecutionResult -> deterministic + optional
DeepEval checks -> redacted report -> optional LangSmith scores.

Each case gets its own process and unique product run ID. Cancellation kills and
reaps the process. Company scope is trusted configuration, never an instruction
from the case. Only allowlisted `metadata.odin_parameters` reach the target;
golden expected answers, reference contexts and check definitions do not.
Subprocess stderr is suppressed and exceptions are reported by type to avoid
accidental credential/request-body disclosure.

Targets are `ask`, `retrieval`, `analysis`, `event`, `update`, `tool_probe`.
Graphs that write data require `disposable_database=true`. This is an explicit
operator assertion, not a technical guarantee that a supplied URL is disposable.
Use a separate database/company and reset it between experiments. Cases can
affect subsequent graph cases through persisted state; default concurrency is 1.
External send/file-write tools are fenced inside evaluation, including privileged
system tools. Internal write_state tools also require the disposable database
opt-in, including when invoked through tool probes. This fence is evaluation
policy, not a production injection guard.
Tests of product allowlists/approvals name the exact expected denial exception.

The collector inherits context across LangGraph fan-out and Odin's `pmap`, locks
record appends, and caps memory (10,000 records / 16 MB by default). Capped evidence
is partial and required checks skip. Missing evidence never becomes a pass.
Retrieval includes complete text, stable clause/version identity and the source
row's tenant label. Empty retrieval is explicitly recorded. Ask metrics receive
the actual 1,500-character passages and rendered tool messages supplied to the
answer model, not full unseen candidates. Complete source observations are kept
separately in `observed_documents` for security checks; `model_context` feeds the
judge. Agent events include start/end and inter-agent messages; tool records
contain one terminal decision, so denied calls are not counted as executions.
Graph output includes persisted artifacts tagged with that execution's run ID;
reused artifacts written in earlier runs may not appear in that list. Recomputed
artifacts now carry the new writer's run ID. Set `force=true` for extraction
comparisons and use a clean evaluation database.

Ask now refuses absent/unverifiable citations instead of exposing an unsupported
answer. This is citation verification, not proof of semantic entailment; the
DeepEval faithfulness check evaluates grounding separately.

## LangSmith

- `ragnarok-odin`: product spans for ask, retrieval, structured calls, agents and
  tools; LangGraph/provider child spans inherit the scoped client.
- `ragnarok-evaluation`: case score/status feedback, with a `product_trace_id`
  correlation field when a product trace was created.

Product instrumentation is centralized in `odin/core/telemetry.py`, without
scattered `@traceable` decorators. Inputs and outputs are hidden in the scoped
client; local environment files also set the SDK hiding flags for auto tracing.
Only evaluator status/score/timing and hashed case IDs are published. Product
metadata still contains operational identifiers. Reports remain local and can
contain commercially sensitive contract text despite known-secret redaction.
Review them before sharing. Automatic child exception text is sanitized before
it reaches the SDK transport; hiding I/O is still not a general-purpose PII filter
for user-authored metadata.

Tracing is opt-in per evaluator config (`odin.product_tracing` separately from
`tracing.enabled`). Observer publishing failures are warnings, not score changes.
Model judges remain opt-in and require their own model-provider credentials.
Both product/feedback uploads and readback were verified with a synthetic-only
LangSmith smoke test; no contract data or model calls were needed:

```powershell
uv run --env-file .env --all-extras python examples/langsmith_smoke.py
```

## Golden runs

Schema and authoring instructions are in `datasets/golden/README.md`. Configs
deliberately await real dataset files; they do not use fake expected answers.
Replace the company placeholders and seed matching contract versions in the
disposable database, then:

```powershell
uv run --all-extras ragnarok validate datasets/golden/rag.json
uv run --env-file .env --all-extras ragnarok run --config configs/odin.retrieval.json
uv run --env-file .env --all-extras ragnarok run --config configs/odin.rag.json
uv run --env-file .env --all-extras ragnarok run --config configs/odin.agent.json
uv run --env-file .env --all-extras ragnarok run --config configs/odin.rag-security.json
```

Existing five DeepEval RAG metrics use real question/answer/context mappings.
Deterministic agent checks cover tools/arguments/errors, message ordering, bounded
activity and exact structured fields. Retrieval adds MRR@k alongside recall/hit.
Security covers tenant labels, canaries, forbidden/unauthorized execution,
approval policy and explicit denials. This is invariant evaluation, not a
certification of all possible attacks. Model accuracy, conflict/alert precision
and timeline goldens await reviewed labels. Failed/incomplete agent work remains
partial even when an individual assertion passes. Fake-provider output is an
execution error unless `allow_fake_provider=true` is explicitly used for smoke QA.

Offline tests use SQLite, BM25-only retrieval, an in-memory graph checkpointer and
the schema-only fake provider. PostgreSQL/pgvector dense search, actual provider
answers and golden accuracy are not yet verified. `retrieval.dense_enabled=false`
is an explicit retrieval ablation; production hybrid retrieval defaults to true.
Product budget counters omit some failed provider attempts, so exact token/cost
usage remains unavailable rather than inventing complete accounting. Adapter
latency includes worker startup and any final trace flush. The stock HTTP adapter
is still available, but the current API's ordinary JSON responses omit the full
evidence needed for these checks; no public debug/evaluation endpoint was added.
