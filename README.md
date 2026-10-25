# RAGNAROK - Odin

Multi-agent contract intelligence with a connected RAG, agent evaluation, security
and LangSmith tracing pipeline.

## Repository layout

Run commands from this folder, the Git repository root. There is one backend directory.

```text
Ragnarok/
  backend/odin/     Product API, agents, graphs, retrieval and services
  backend/tests/    Product unit tests
  frontend/         Team frontend integration directory
  ui-dev/           Reference UI wired to the API
  src/ragnarok/     Evaluation and security pipeline
  tests/            Evaluator and integration tests
  corpus/           Contract inputs, scenarios and evaluator-only goldens
  configs/          Evaluation run configurations
  config/           Product runtime configuration
  docs/             Checkpoint handoff and measured results
```

## Setup and offline checks

Python 3.11 and uv are required.

```powershell
uv sync --locked --all-extras
uv run --locked --all-extras ragnarok corpus-build
uv run --locked --all-extras pytest -q
```

On Windows, `./scripts/checkpoint.ps1` runs the offline checkpoint checks.
CI runs offline checks on Windows and Linux after pushing. Tests do not make
paid provider calls or send mail.

Create a private `.env` from `.env.example` and supply your own provider,
LangSmith and database settings. Never commit `.env`, tokens or local reports.

## Product API

With a working PostgreSQL/pgvector database:

```powershell
uv run --env-file .env --all-extras uvicorn --app-dir backend odin.api.main:app --port 8000
```

The existing Docker setup is available through `docker-compose.yml`. The API
supports Google/dev login; configured Gmail polling starts with the API lifecycle.
No external mail is sent by evaluation workers.

## Evaluation checkpoint

See [setup and teammate handoff](docs/CHECKPOINT.md),
[measured results and remaining work](docs/CHECKPOINT_RESULTS.md),
[corpus documentation](corpus/README.md) and [input schemas](docs/SCHEMAS.md).
Live model evaluation is explicit through `configs/corpus.*.json`; goldens never
enter product prompts. The checkpoint is ready for frontend development and
further evaluation improvements, with known quality gaps retained in reports.
