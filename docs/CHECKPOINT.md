# Corpus evaluation checkpoint

This repository now contains the backend, corpus, evaluator, locked Python
dependencies, configs, tests and CI. Work from this repository root; no parent
workspace files are required. Frontend work is unchanged.

## Fresh clone

```powershell
git clone https://github.com/ManasT10-14/AttentionIsAllYouNeed.git
cd AttentionIsAllYouNeed
git switch corpus
uv sync --locked --all-extras
uv run --locked --all-extras ragnarok corpus-validate
uv run --locked --all-extras ragnarok corpus-build
uv run --locked --all-extras pytest -q
```

On Windows, `./scripts/checkpoint.ps1` runs the offline checkpoint checks.
GitHub Actions runs the offline suite on Windows and Linux after pushing.
Live providers and Gmail are never used by the ordinary test suite or CI.

Copy `.env.example` to an ignored `.env` and supply your own provider/LangSmith
credentials. Existing shell settings override the file. The parser correctly
handles quotes, comments and empty provider keys. The `api` extra installs the
API/auth/Gmail dependencies too; the full dependency set is captured in uv.lock.
Backend application startup still needs a working PostgreSQL/pgvector database.
The supplied local database login failed authentication during this checkpoint;
the evaluator therefore uses dedicated SQLite databases under ignored work/.
It does not overwrite or initialize the configured production database.

## What is evaluated

The authored corpus has 15 PDFs, 43 pages, 64 scenarios, 384 agent vectors,
114 typed Thor assertions and 276 source citation units. These expectations are
author-created and have not been independently reviewed by a legal expert.
Validation checks hashes, actual PDF pages/quotes, release visibility and source
references. The original corpus validators also check fixture arithmetic and
deterministic PDF regeneration. Validation is separate from actual model results.

`ragnarok corpus-build` compiles five datasets under datasets/corpus/:

- `retrieval.json`: all 276 citation queries. Gold table rows are mapped to the
  actual source SCHEDULE chunk containing their quote, independently of results.
- `rag.json`: all 276 queries with reference answers, full trusted source chunks
  and DeepEval checks. `checkpoint-baseline` selects one reference across each
  of the 15 contracts. Citation checking tolerates PDF whitespace, not changed words.
- `thor.json`: all 15 per-contract extraction goldens and their 114 typed facts.
  Deterministic field mappings are explicit; unmapped facts remain visible gaps.
  The rubric compares semantic facts, not an exhaustive oracle JSON layout.
- `agent.json`: all 384 role/scenario vectors. The checkpoint config selects the
  six PAY-03 role vectors; remove include_tags to deliberately run the full set.
  A scenario executes once, then all six roles are scored from its actual state.
- `security.json`: direct injection, document-embedded injection and foreign-tenant
  canary tests. The modified document/private row exist only inside an isolated
  test database; canonical corpus PDFs are unchanged.

The trusted loader releases PDFs/events only when permitted by the scenario and
received_at clock. C08 stays hidden before arrival. Actual earlier checkpoint
state supplies later work; future schedules and oracle files are not model inputs.
Source-unit RAG/Thor tests intentionally inspect one selected PDF, including C08,
outside an operational scenario; they do not populate initial scenario state.

The product still has coverage gaps: generic extraction fields cannot express
every authored rate/cap/deadline, its clock stores dates rather than full UTC
timestamps, and not every logical financial assertion has a backend mapping.
Reports retain these gaps and incomplete work; they do not create expected values
to make tests pass. Backend domain improvements can now be measured iteratively.

## Live baseline and tracing

```powershell
uv run --env-file .env --all-extras ragnarok run --config configs/corpus.retrieval.json
uv run --env-file .env --all-extras ragnarok run --config configs/corpus.thor.json
uv run --env-file .env --all-extras ragnarok run --config configs/corpus.rag.json
uv run --env-file .env --all-extras ragnarok run --config configs/corpus.agent.json
uv run --env-file .env --all-extras ragnarok run --config configs/corpus.security.json
```

`./scripts/checkpoint.ps1 -Live` runs the representative baseline above and
preserves quality/infrastructure failure exit codes. It makes paid model calls.
RAG/agent DeepEval judges use `odin:openai`, which honors the configured compatible
endpoint, model, key and project header. Structured judge output is schema
validated, including legitimate JSON-content responses when a provider omits
a tool call. No missing verdict or score is invented.

Product spans go to ragnarok-odin; scores/status feedback go to
ragnarok-evaluation and link to product_trace_id. Inputs/outputs are hidden and
child exceptions are sanitized. Actual trace/feedback readback is part of the
checkpoint verification. Local reports can contain contract data and remain
ignored; only a sanitized summary belongs in version control.

For metric-only changes, re-score saved observations without product calls:

```powershell
uv run --env-file .env --all-extras ragnarok run --config configs/corpus.thor.json --recorded-report reports/corpus-thor.json --output reports/corpus-thor-rescored.json
```

The dataset hash must match. The source report cannot be overwritten. Product
trace IDs and original execution latency are retained; recorded_run_id identifies
the source evaluation. Original deterministic security outcomes, and deterministic outcomes on redacted
evidence, are retained. Unredacted quality/agent observations can be re-scored. Redacted evidence is never sent to
a new judge. Judge calls/feedback uploads still occur when enabled.

Add `--retry-judge-errors` to retry only failed provider/judge operations while
retaining completed assessments, with concurrency reduced to one. This does not
rerun product calls or turn a recorded safety failure into a pass.

Latency scope is explicit: batched retrieval records each actual search duration;
all role vectors sharing a graph retain the same whole-scenario worker duration.
Cache lookups are not reported as product execution. Earlier pre-fix cached
latencies in historical baseline reports should not be used as a benchmark.

Default checkpoint retrieval is explicitly BM25-only. Dense-memory cosine search
is available for SQLite evaluation by setting corpus.dense=true; PostgreSQL keeps
its existing pgvector backend. Do not claim dense/pgvector validation from a
BM25-only report. Exact provider cost accounting also remains unavailable because
the existing budget does not charge all failed attempts.

## Sharing this checkpoint

Push the verified corpus commit, then teammates can pull corpus and use the
commands above. Keep .env, tokens/, work/, reports/, model caches and local
databases out of Git. Evaluation quality failures are a baseline for improvement;
an engineering checkpoint is not a claim that every golden assertion passes.
See CHECKPOINT_RESULTS.md for the measured scope, results and remaining work.
