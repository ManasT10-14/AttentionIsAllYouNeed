# RAGNAROK · Odin — multi-agent contract intelligence

Odin orchestrates five agents in LangGraph:
- **Thor** extracts terms, with a citation for every field.
- The **Norns** build the timeline on a simulated clock and project the worst case.
- **Loki** attacks the contracts adversarially, within one contract and across contracts.
- **Heimdall** watches the company Gmail inbox for events and verifies Loki's claims.
- **Tyr** rules on disputes and drafts notices and amendments.

Every agent capability is an audited tool. Hook points are ready for the future security and eval suites
(see `evals/README.md`). The input formats are in **`docs/SCHEMAS.md`**.

## Run locally
```bash
docker compose up -d db                                # Postgres + pgvector
cd backend && py -3.11 -m venv .venv && .venv/Scripts/pip install -r requirements.txt
cp ../.env.example ../.env                             # fill in keys (see below)
.venv/Scripts/python -m uvicorn odin.api.main:app --port 8000
cd ../ui-dev && npm install && npm run dev           # http://localhost:5173  (or `npm run build` → served by :8000)
```
Steps in the app:
1. Log in, either with Google or with dev login.
2. On the **Contracts** tab, click **Demo: seed sample contracts**, or upload your own.
3. Open **Overview** to see the time slider, exposure and heatmap.
4. Open **Events** to play the scripted emails or to send judge emails.

Full Docker setup: `docker compose --profile full up --build` (ui-dev must be built first).

## LLM providers (`config/odin.yaml`)
Every agent tries the providers in this order: **Bedrock (OpenAI-compatible endpoint) → OpenAI → Claude → Groq**.
- Providers without a key are skipped.
- Each agent can override the order under `agents:`.
- `ODIN_FORCE_PROVIDER=fake` runs everything offline with a stub LLM, for smoke tests only.

## Google login + Gmail (Heimdall)
1. In Google Cloud, create an OAuth client (Web).
2. Set the redirect URI to `http://localhost:8000/auth/google/callback`.
3. Enable the Gmail API.
4. Add the company account as a test user.
5. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.

Scopes: `gmail.readonly`, `gmail.modify` (for labels) and `gmail.send` (auto-replies and approved notices).
The poller checks the inbox every 15 seconds. **Poll Gmail now** on the Events tab forces an immediate check.

## Layout
```
backend/odin/
  core/       models (all schemas), config, budget, hooks, citation guard, run context, SSE bus
  llm/        provider factory + fallback chain + structured output + bounded tool loop
  tools/      ToolRegistry (allowlists, hooks, approvals, audit) + every agent tool
  agents/     odin, thor, norns, loki, heimdall, tyr, synth  (+ prompts/*.md)
  graphs/     analysis (fan-out), contract_ws (per-contract loops), event, update
  retrieval/  hybrid BM25 + dense (bge-small, pgvector) + RRF; reranker slot reserved
  ingest/     PDF/DOCX → clauses with highlight boxes; version diff
  services/   timeline engine (Norns), insights, events, ask, amend, demo, reports
  email/      Gmail client, poller, strict event parser
  api/        FastAPI routes, auth (Google OAuth + dev login), SSE
frontend/     team UI (owned by the UI teammate)
ui-dev/       placeholder React UI wired to every API endpoint (reference for the team UI)
```

## Tests
`backend/.venv/Scripts/python -m pytest backend/tests -q`
