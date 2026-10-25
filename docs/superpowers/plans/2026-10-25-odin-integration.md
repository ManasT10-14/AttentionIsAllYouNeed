# Odin integration design and execution plan

Source: AttentionIsAllYouNeed at e550f874181ce992053dcc08f523b6842d37bd94
(actual checkout revision is also recorded in integration reports).

The existing independent evaluator stays at the workspace root. The product is
cloned in `backend/` on `feat/ragnarok-evaluation`; no remote push is requested.
Direct hook integration is chosen over HTTP-only scoring: HTTP currently omits
complete retrieval, tool decisions and workflow evidence. The existing generic
HTTP and Graph adapters remain usable.

Each Odin case runs in a disposable subprocess, with a trusted company scope
from configuration, a unique run ID, captured hook observations, and an enforced
timeout that terminates the worker. Supported targets: ask, retrieval, analysis,
event and update graphs, and explicit registry security probes. Write-producing
graphs require explicit disposable-database opt-in. External sends/file writes
are blocked by an evaluation guard even when the dataset requests them.

The product emits full retrieval records (including row-owned company ID),
single terminal tool records with allowlist/approval/execution decisions, agent
node outcomes, and messages. Collection uses contextvars and a locked bounded
buffer, so concurrent graph branches share only their own case's evidence.
Truncated or missing evidence remains partial; no fabricated completeness.
RAG answer context uses the actual truncated passages given to the model;
retriever evaluation uses full ranked retrieval. Citation IDs include contract,
version and clause; golden labels must use the same stable identity.

LangSmith product traces use shared boundary instrumentation and hidden inputs
and outputs. Evaluator runs publish scores separately and link product trace IDs.
The provided key is stored only in ignored local environment files. Model judges
remain opt-in. Synthetic tests are engineering checks, never golden accuracy.

## Tasks

- [x] 1. Add failing integration tests, backend optional dependencies and hook capture.
- [x] 2. Complete product retrieval/tool/agent telemetry and evaluation sandbox guard.
- [x] 3. Add isolated Odin adapter/worker and CLI configuration with golden-ready suites.
- [x] 4. Add centralized private LangSmith tracing and verify a synthetic live upload.
- [x] 5. Run both test suites, CLI smoke, lint/build, independent review, document limits.

## Review focus

Empty retrieval must be observable; permission denial must not count as execution;
tool body exceptions must count as attempts; parallel records must be isolated;
timeouts must kill workers; golden answers must never be passed to the product;
source tenant labels must not be copied from the requested company; trace errors
must not break the product; fake providers must be identified and rejected by
golden configs; missing telemetry must not become passing security checks.
