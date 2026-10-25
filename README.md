# RAGNAROK - Odin

Multi-agent contract intelligence with a connected RAG, agent evaluation, security
and LangSmith tracing pipeline.

## Repository layout

Run every command from the repository root.

```text
backend/            Odin product (owned by the backend team)
  odin/             API, agents, graphs, retrieval, ingestion, services
  config/odin.yaml  Agent models, loop limits, budgets and thresholds
  tests/            Product unit tests
  Dockerfile, requirements.txt
eval/               Evaluation and security pipeline (owned by the eval team)
  ragnarok/         Evaluator package and `ragnarok` CLI
  tests/            Evaluator and integration tests
  configs/          Evaluation run configurations
  datasets/         Compiled datasets (corpus/ is rebuilt by `ragnarok corpus-build`)
  examples/         Mock product and LangSmith smoke example
corpus/             Contract inputs, scenarios, evaluator-only oracle
  samples/          Six demo contracts, company context and demo emails (used by Demo seed)
frontend/           Team UI
ui-dev/             Reference UI wired to every API endpoint
scripts/            make_samples.py, checkpoint.ps1
  corpus/           Corpus generators and validators
docs/               Current specs and handoffs
  archive/          Superseded plans and progress logs
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

Start the database with `docker compose up -d db` (PostgreSQL 16 + pgvector, user, password and
database all `odin`, port 5432). `DATABASE_URL` in `.env` must match it:
`postgresql+psycopg://odin:odin@localhost:5432/odin`.

If login fails with "password authentication failed for user odin":
- A native PostgreSQL service on Windows may already own port 5432, so the app reaches it instead of
  Docker. Stop that service, or map Docker to another port and change `DATABASE_URL` to match.
- The Docker volume was first created with a different password. The password only applies on first
  start. Run `docker compose down -v` (this deletes local data), then `docker compose up -d db`.

Then run the API:

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
Live model evaluation is explicit through `eval/configs/corpus.*.json`; goldens never
enter product prompts. The checkpoint is ready for frontend development and
further evaluation improvements, with known quality gaps retained in reports.
