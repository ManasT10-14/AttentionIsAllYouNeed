# Connected evaluation and security suite

The installable Ragnarok evaluator is in the parent workspace, one level above
this backend checkout. Instructions: `../docs/odin-integration.md` from the
checkout root, or `../../docs/odin-integration.md` from this folder.

From the parent workspace:

```powershell
uv sync --locked --all-extras
uv run --locked --all-extras pytest -q
uv run --env-file .env --all-extras ragnarok run --config configs/odin.security.json
```

The suite uses request-scoped hook subscribers. Retrieval records full ranked
source clauses and empty results. Tool records include authorization, approval,
function-entry and terminal outcome. Agent start/end and messaging events support
trajectory checks. Direct clause reads are observed too. Capped capture buffers
mark evidence partial.

Workers call Ask Odin, the retriever or actual analysis/event/update graphs.
Ordinary API responses omit this evidence, so no public debug route was added.
Writes require an explicitly disposable evaluation database and external tool
effects are fenced. Security probes require explicit expected denial types.

LangSmith instrumentation is centralized in `odin/core/telemetry.py`. A scoped
client hides inputs/outputs and sanitizes outgoing exception text for child
traces. Evaluator scores are published separately and linked by product trace ID.
Configuration and keys come from ignored environment files.

Golden configs live in the parent workspace's `configs/odin.*.json` and await
reviewed datasets under `datasets/golden/`. Fake providers are rejected by default.
Model accuracy and dense retrieval require a real evaluation database/provider.
