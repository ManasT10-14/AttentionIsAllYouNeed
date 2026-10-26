# Official pack integration — 26 October 2026

The Quillhub organiser pack is a separate dataset under `corpus/odin_dev_pack/`. It does not replace or alter the original 15-contract corpus. Import requires an empty workspace, preventing mixed company/context data.

## Start and test

From the repository root in a normal local terminal:

```powershell
docker compose up -d
$env:PYTHONPATH = 'backend'
.venv\Scripts\python.exe -m uvicorn odin.api.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm run local
```

Open `http://127.0.0.1:3000`, sign into an empty development workspace, and use **Contracts → Import official bundle**. This imports the canonical TXT/PDF pairs, context, ledger and holidays and starts portfolio analysis. Wait for analysis to finish in Agent runs before replaying events.

1. Open Simulation, load Drop 1, then play to 15 March 2027.
2. Inspect the event feed, checkpoint and drafted actions. A failed or incomplete assessment requires review and is not evidence of a successful legal analysis.
3. Load Drop 2 and play to 1 June, then 15 September. The malformed line is quarantined separately; valid events continue.
4. Ask Odin about amendments, exclusivity, insurance, recovery gaps and milestone deadlines. Answers include governing family documents and exact source quotes. Check substantive model quality against the source contracts.
5. Gmail remains a separate optional source for external reports. No email is sent by importing or replaying the pack. Automatic rejection replies are disabled.

The legacy demo seed/play controls now delegate to the official pack. Normal `/clock` mutation is blocked in an official simulation; use Simulation controls for chronological replay. Loading a drop queues future events separately from agent-visible events. Loading/playing again is idempotent; reset preserves contracts and archived run history, removes current reports and drop event data, and requires fresh report generation. Reset refuses to remove approved/executed actions.

## Implemented API

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/bundle/import?analyze=true` | Validate manifest/twins, import, optionally analyze |
| GET | `/api/ledger` | Ledger rows dated on or before the current clock |
| GET | `/api/holidays` | Provided observed holiday schedule |
| GET | `/api/simulation` | Clock, loaded drops, pending count and run status |
| POST | `/api/simulation/drops/1/load` | Queue Drop 1; use `2` for Drop 2 |
| POST | `/api/simulation/step` | Assess the next queued event |
| POST | `/api/simulation/play` | Body `{"until":"2027-03-15"}`; background sequential replay |
| POST | `/api/simulation/advance` | Body `{"to":"2027-06-01"}`; same replay semantics |
| GET | `/api/simulation/checkpoints` | Saved checkpoint evidence and completeness indicator |
| POST | `/api/simulation/reset` | Reset the staged replay |

Mutations require admin; all data is tenant-scoped. Step/play/advance return a run ID, and completion/errors are exposed in simulation state and Agent runs. Wait for the active run before another mutation. Optional analysis and event assessment use the configured model provider; deterministic parsing/replay tests do not prove model answer quality.

## Verification performed

- 101 backend product tests passed, including seven new pack workflow tests. Evaluator/oracle files were excluded and not read.
- 73 frontend tests and TypeScript checking passed.
- Next.js production build passed with all 22 routes, including Simulation. A separate build directory was used because the existing `.next` tree denied writes.
- Functional tests used actual pack sources and an isolated SQLite database with dense embeddings disabled. They verified import, all canonical clause spans, amendment links, idempotence, staged replay, rejection of malformed JSON, three chronological snapshots, observed-holiday deadlines, exact citation checks, tenant isolation and API handlers/validation.
- Network HTTP/ASGI-client execution could not be completed: this session denies TCP connections, including Python's Windows event-loop socket pair. Handler tests and OpenAPI generation passed; these are not a live browser/backend verification.

## Environment limits

GitHub DNS/network access was denied, so completeness was verified against the existing local manifest, including all eight PDF twins, documentation, event drops and clock. Remote freshness was not verified.

Docker access and PostgreSQL connections were denied. The compiled UI process reported ready on port 3001, but the browser timed out and localhost requests were denied; that verification process was stopped. The full application, live model answers, embeddings, LangSmith and Gmail therefore remain unverified in this session.

The checkout remained on `integration`: creating the requested `corpus` branch failed because `.git` is read-only. Changes remain uncommitted; no push or deployment was performed.
