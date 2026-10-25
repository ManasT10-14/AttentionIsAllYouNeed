# RAGNAROK · Odin

Multi-agent contract intelligence. Odin plans the work, Thor extracts every term with a citation,
the Norns build the timeline on a simulated clock, Loki attacks the contracts, Heimdall watches the
company Gmail inbox and verifies Loki's claims, and Tyr rules on disputes and drafts the notices.
Every claim links back to the exact clause, highlighted in the original PDF.

The repository also holds the evaluation and security pipeline (`eval/`) and the 15-contract test
corpus (`corpus/`).

## Status

| Part | State |
| --- | --- |
| Backend (`backend/`) | All FR1–FR9 and NFR1–7 flows run end to end on real models (Bedrock Mantle). Full analysis of 6 contracts takes about 5 minutes; one email event about 2.5 minutes. |
| Team UI (`frontend/`) | Next.js app, connected to the live backend through its dev proxy. Login, overview, slider, graph, debate, alerts and actions, events, PDF reference viewer and the live feed were checked in a browser. |
| Gmail (Heimdall) | Verified: a real `[ODIN-EVENT]` email produced violations, highlights, alerts and drafted actions. |
| Evaluation (`eval/`) | 165 offline tests pass. Live Thor run: 85 of 114 golden assertions matched. |

Known gaps are listed under [Known gaps](#known-gaps).

## Repository layout

Run every command from the repository root unless a step says otherwise.

```text
backend/            Odin product
  odin/             API, agents, graphs, retrieval, ingestion, services
  config/odin.yaml  Agent models, loop limits, budgets and thresholds
  tests/            Product unit tests
eval/               Evaluation and security pipeline
  ragnarok/         Evaluator package and `ragnarok` CLI
  tests/            Evaluator and integration tests
  configs/          Evaluation run configurations
  datasets/         Compiled datasets (corpus/ is rebuilt by `ragnarok corpus-build`)
  examples/         Mock product and LangSmith smoke example
corpus/             15 test contracts, scenarios, evaluator-only oracle
  samples/          6 demo contracts, company context and demo emails (used by "Demo seed")
frontend/           Team UI (Next.js)
scripts/            make_samples.py, checkpoint.ps1; corpus/ holds corpus generators and validators
docs/               Specs and handoffs; archive/ holds superseded plans
```

## 1. Prerequisites

| Tool | Version | Used for |
| --- | --- | --- |
| Docker Desktop | any recent | PostgreSQL 16 + pgvector |
| Python | 3.11 | Backend and evaluator |
| uv | 0.13 or later | Python environment (`pip install uv` works) |
| Node.js | 20 or later | Team UI |
| LibreOffice | optional | Exact DOCX to PDF conversion; a built-in fallback is used without it |

Behind a TLS-intercepting network (corporate or college proxy), add `UV_NATIVE_TLS=1` before uv
commands and `NODE_OPTIONS=--use-system-ca` before npm commands.

## 2. One-time setup

### 2.1 Python environment

```powershell
uv sync --locked --all-extras
```

### 2.2 Secrets file

Copy `.env.example` to `.env` and fill in the values. Ask the backend lead for keys over a private
channel. `.env` is git-ignored: never commit it, paste it or screenshot it.

| Setting | What to put |
| --- | --- |
| `OPENAI_API_KEY` | Bedrock Mantle API key (main model provider) |
| `OPENAI_BASE_URL`, `OPENAI_PROJECT_ID` | Keep the values from `.env.example` |
| `BEDROCK_API_KEY` | Same key, used as the second-region fallback |
| `DATABASE_URL` | Keep the default unless you changed the database |
| `SECRET_KEY` | Any long random string |
| `FERNET_KEY` | Generate once: `uv run python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | From the Google Cloud OAuth client (section 2.4) |
| `PUBLIC_BASE_URL`, `FRONTEND_URL` | `http://127.0.0.1:3000` for the team UI |
| `LANGSMITH_API_KEY` | Optional, turns on tracing |
| `ODIN_FORCE_PROVIDER` | Leave empty. Set to `fake` to run without any model key (stub answers) |

### 2.3 Team UI

```powershell
cd frontend
npm ci
copy .env.example .env.local
cd ..
```

The defaults in `frontend/.env.example` already point the UI's proxy at the backend on port 8000.

### 2.4 Google login and Gmail (only for the live email demo)

In Google Cloud Console, for the project that owns the OAuth client:

1. Enable the **Gmail API**.
2. **OAuth consent screen**: keep it in **Testing**, and add the company inbox account under
   **Test users**. Accounts not on this list get "Error 403: access_denied".
3. **OAuth client** (Web application): add the authorised redirect URI
   `http://127.0.0.1:3000/auth/google/callback`. It must match `PUBLIC_BASE_URL` exactly; `localhost`
   and `127.0.0.1` count as different addresses.

Testing-mode Google tokens expire after 7 days, so sign in again the day before a demo.

## 3. Run everything

Use three terminals, all starting at the repository root.

**Terminal 1: database**

```powershell
docker compose up -d db
```

**Terminal 2: backend (API, agents, Gmail poller) on port 8000**

```powershell
uv run --env-file .env --locked --all-extras uvicorn --app-dir backend odin.api.main:app --port 8000
```

Check it: http://localhost:8000/api/health returns `{"ok":true}`.

**Terminal 3: team UI on port 3000**

```powershell
cd frontend
npm run dev
```

Open **http://127.0.0.1:3000** (use `127.0.0.1`, not `localhost`, so the login cookie matches).

The sidebar shows **Live feed · live** when the UI is receiving live updates from the backend.

### Without a backend

On the sign-in page, **Explore demo workspace** opens the UI with clearly labelled sample data. It
cannot upload, run agents or send email.

## 4. Demo script

Before judging, seed the company once so nobody waits for the 5-minute analysis.

1. **Sign in.** Use **Continue with Google** with the company inbox account. For a local
   run, use **Development login** with any email; each email is its own company.
2. **Load contracts.** On **Contracts**, choose **Seed backend demo**. The 6 sample contracts
   are uploaded and analysed (about 5 minutes; the Overview workplan fills in live). You can also upload
   your own PDF or DOCX files in the format described in `docs/SCHEMAS.md`.
3. **Overview.** Priority alerts with clause links, financial exposure (expected and worst case),
   contract health and the analysis workplan per contract.
4. **Time slider.** Drag the simulated date forward. Deadlines, missed payments, alerts and exposure
   recompute instantly.
5. **Graph.** Contracts, parties and risky clauses; dependency and conflict edges. Pick an agreement
   under **Explore downstream impact** to see the cascade.
6. **Debate.** Loki's attack, Heimdall's support or challenge, and Tyr's ruling for each finding, with
   citations.
7. **View references.** Click any clause chip (for example MSA-2026-001 · §SCHEDULE A). The original
   PDF opens at the right page with the clause highlighted.
8. **Live email event.** From any other account, send `corpus/samples/emails/01_payment_late.txt` to the
   company inbox. Copy the subject line as the email subject and the rest as the body. Within about
   15 seconds (or press **Check for new emails** on **Events & Inbox**), Heimdall maps it to the clauses,
   violations appear with highlights, Tyr confirms them and drafts actions, and alerts update live.
   - `02_outage.txt` shows an SLA breach.
   - `04_malformed.txt` is rejected, and the sender gets an auto-reply with the correct format.
   - `05_noise.txt` is filtered out as noise.
   - Without Gmail, **Replay sample emails** on **Events & Inbox** plays them without Gmail, or submit a manual event there.
9. **Alerts & Actions.** Drafted notices and amendments with clause citations and confidence. An admin
   approves, then sends (by Gmail) or applies (an amendment creates a new contract version).
10. **Ask Odin.** Ask questions in plain English; answers cite clauses, or say there is not enough
    evidence.
11. **Reports.** Per-contract reports and the company risk report, with PDF export.
12. **Observability.** Runs, per-agent calls, tokens and cost, tool audit, citation-guard results.

## 5. Tests and evaluation

Offline (no model calls, no email):

```powershell
uv run --locked --all-extras pytest -q
uv run --locked --all-extras ruff check eval
cd frontend; npm run typecheck; npm test; cd ..
```

Corpus checks (the same steps CI runs):

```powershell
uv run --locked --all-extras ragnarok corpus-validate
uv run --locked --all-extras python scripts/corpus/validate_corpus.py
uv run --locked --all-extras python scripts/corpus/validate_golden.py
uv run --locked --all-extras ragnarok corpus-build
```

Live evaluation (paid model calls; results go to `reports/`, which is git-ignored):

```powershell
uv run --env-file .env --locked --all-extras ragnarok run --config eval/configs/corpus.thor.json
```

Other stages: `corpus.retrieval`, `corpus.rag`, `corpus.agent`, `corpus.security`. See
`docs/CHECKPOINT.md` and `docs/CHECKPOINT_RESULTS.md` for what each measures and the latest results.

## 6. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `password authentication failed for user "odin"` | A Windows PostgreSQL service may already own port 5432; stop it, or map Docker to another port and update `DATABASE_URL`. If the Docker volume was created with another password, run `docker compose down -v` (deletes local data) and start again. |
| Google shows `Error 403: access_denied` | Add that account under **Test users** on the OAuth consent screen. |
| Google shows `redirect_uri_mismatch` | Register exactly `<PUBLIC_BASE_URL>/auth/google/callback` in the OAuth client. |
| Logged in, but the UI goes straight back to sign-in | Open the UI at the same address as `FRONTEND_URL` (`127.0.0.1` and `localhost` are different). |
| Sidebar stays on **Live feed · connecting** | Restart `npm run dev` after pulling (the dev proxy must not compress the stream), and make sure the backend is running. |
| `certificate verify failed` / `SELF_SIGNED_CERT_IN_CHAIN` | Use `UV_NATIVE_TLS=1` for uv and `NODE_OPTIONS=--use-system-ca` for npm. |
| Email sent, nothing happens | The subject must start with `[ODIN-EVENT]`; open **Events & Inbox** to see the inbox status, then press **Check for new emails**. |
| Port 8000 or 3000 already in use | Stop the old process, or change the port and the matching URLs in `.env` and `frontend/.env.local`. |

## Known gaps

- Thor does not yet fill every evaluation golden; 29 of 114 are still missed, mostly one-off
  identifiers and free-text rules.
- The simulated clock works in dates; exact times are kept on deadlines only (`due_at`).
- Some dependency directions between contracts look wrong, so cascade alerts can mislead.
- Heimdall is the slowest agent (about 40 seconds per call on its current model).
- Team UI: the graph opens zoomed out, and a few fields still show "Not provided" where the
  backend uses a different field name (see `docs/api-samples/` for real responses).
- Model prices in `backend/config/odin.yaml` are placeholders, so the cost meter is approximate.

## More documentation

- `docs/SCHEMAS.md`: contract, company context and event email formats
- `docs/UI_COMPONENTS.md`, `docs/FRONTEND_CONTRACT.md`, `docs/api-samples/`: API contract for the UI
- `docs/CHECKPOINT.md`, `docs/CHECKPOINT_RESULTS.md`: evaluation workflow and results
- `docs/Odin_Technical_Handoff.docx`: architecture briefing for new teammates
- `frontend/README.md`, `frontend/INTEGRATION.md`: team UI details
