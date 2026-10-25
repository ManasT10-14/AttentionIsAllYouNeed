# Odin UI component specification (for the frontend team)

Status: the backend API is live. The placeholder UI under `ui-dev/` is a throwaway reference that shows the
data flows; replace it freely. All data comes from the REST API (`/api/*`, OpenAPI at `/docs`), plus one
live stream (`GET /api/stream`, Server-Sent Events).

Run `npm run gen:api` with the backend up to get TypeScript types for every endpoint.

**Conventions every component must follow**

| Convention | Rule |
|---|---|
| **SOURCED vs ANALYSIS** | Every value is either clause text (`source: "sourced"`) or agent-generated (`source: "analysis"`). Show a badge. PS NFR2 requires this. |
| **Citation chip** | `{contract_id, clause_number, quote, page, version, verified}`. Click opens the Reference Viewer. `verified=false` gets a warning style ("quote not found in contract"). |
| **Severity** | Alerts: `info · low · medium · high · critical`. Findings: integers 1–5. One colour scale everywhere. |
| **Status pills** | Workstreams: `pending/running/done/partial/failed`. Findings: `open/verified/challenged/ruled/withdrawn/superseded`. Actions: `draft/approved/rejected/sent/applied/superseded`. Violations: `suspected/confirmed/dismissed`. Events: `received/processing/processed/rejected/noise`. Alerts: `open/acknowledged/snoozed/resolved`. |
| **Money** | `{amount, currency}`. Format en-IN for INR (`₹ 4,50,000`). Totals are single-currency (FX conversion is not done). |
| **Simulated clock** | Most views take `?as_of=YYYY-MM-DD`. The time slider changes it. `POST /api/clock` commits it. |
| **Live updates** | SSE messages are `{"kind": …, "data": …}`. Re-fetch the affected view on: `agent_message`, `run`, `finding`, `verification`, `ruling`, `action`, `alert`, `violation`, `event`, `extraction`, `report`, `email`, `clock`. Debounce bursts (about 500 ms). |
| **Roles** | `admin` (today) and `super_admin` (future). Only admins see approve/send/apply/upload buttons (`GET /api/auth/me → user.role`). |
| **Empty, loading and error states** | Required for every component listed below. |

---

## A. Shell and auth

| # | Component | Data | Behaviour |
|---|---|---|---|
| A1 | **Login page** | `GET /api/auth/me` (401 means logged out) | "Sign in with Google" goes to `/api/auth/google/login`. A dev-login form (`POST /api/auth/dev-login {email}`) shows only when `dev_login=true`. |
| A2 | **App header** | `/api/auth/me` | Company name, user email and role, sim-clock date, logout (`POST /api/auth/logout`). |
| A3 | **Gmail status / "Connect Gmail" pill** | `me.gmail_connected`, `me.gmail_address`, `me.google_configured` | Connected: "Heimdall listening on X". Not connected: a link to `/api/auth/google/login`, which links the inbox to the current company. |
| A4 | **Global navigation** | n/a | Overview · Contracts · Graph · Debate · Alerts & Actions · Events · Ask · Reports · Observability · (future) Evals · Security · Admin. |
| A5 | **Live-connection indicator** | SSE `ping` every 15 s | Shows reconnecting or offline. |
| A6 | **Toast / notification centre** | SSE `alert` (severity ≥ high), `run` (status change), `email` | Click goes to the related screen. |

## B. Onboarding and contracts

| # | Component | Data | Behaviour |
|---|---|---|---|
| B1 | **Company context uploader** | `POST /api/company/context` (file) → `CompanyContext` | Drop `.md/.txt/.pdf/.docx`. Show the parsed fields (name, currency, approval threshold, jurisdictions, contacts, priorities) for review. |
| B2 | **Contract uploader (multi-file)** | `POST /api/contracts?analyze=true` (files) → `{results[], run_ids[]}` | Each file returns `contract_id, version, is_update, clause_count, warnings[]` or `error`. Flag duplicates and parse warnings. An update starts the update flow. |
| B3 | **Demo seed / re-analyse buttons** | `POST /api/demo/seed`, `POST /api/runs/analysis {force, contract_ids?, max_usd?, max_agent_calls?, max_debate_rounds?}` | Admin only. Optionally expose the budget limits as advanced settings. |
| B4 | **Contract list / table** | `GET /api/contracts` | Columns: id, title, type, parties, version, health score, analysed?, parse warnings. Row opens B5. |
| B5 | **Contract detail page** | `GET /api/contracts/{id}` | Header (title, parties with roles, governing law, version, health with breakdown) plus B6–B11 as tabs. |
| B6 | **Extraction table (Thor)** | `contract.extraction` | One row per field: name, value, confidence %, status (`found/ambiguous/missing/contradictory/unverified`), citation chip, note. Highlight non-`found` rows. |
| B7 | **Ambiguity flags list** | `extraction.flags[]` | Clause, kind, note, related clauses (clickable). |
| B8 | **Clause list** | `contract.clauses[]` or `GET /api/contracts/{id}/clauses?version=` | Number, heading, `clause_type` tag, page, text. Click opens the Reference Viewer. A "history" button opens B10. |
| B9 | **Version list + diff viewer** | `contract.versions[]`, `GET /api/contracts/{id}/diff?from=&to=` | Changes are `added/removed/modified/renumbered`, shown with before (strikethrough) and after (green). |
| B10 | **Clause lineage drawer** | `GET /api/contracts/{id}/lineage/{number}` | The clause text in every version, plus the findings that cited it. |
| B11 | **Health score card** | `GET /api/insights/health` or `contract.health` | Score 0–100 (or "not analysed"). Breakdown: ambiguity flags, unverified fields, open findings, confirmed violations, missed deadlines. |

## C. Reference viewer ("View references", key demo feature)

| # | Component | Data | Behaviour |
|---|---|---|---|
| C1 | **PDF page renderer** | `GET /api/contracts/{id}/versions/{v}/pdf` (pdf.js) | Page navigation and zoom. Deep link: `/viewer?contract=&clause=&v=&violation=`. |
| C2 | **Clause highlight overlay** | `GET /api/citation/resolve?contract=&clause=&v=` → `{page, bboxes:[[page,x0,y0,x1,y1]], text, pdf_url}` | PDF points with a top-left origin; multiply by the render scale. Auto-scroll to the first box. |
| C3 | **Cited-clause side panel** | same response | Exact clause text (SOURCED badge) and clause type. |
| C4 | **Violation context panel** | `GET /api/violations/{id}` | Breach type, who breached, exposure, explanation, triggering event (type, date, description, sender), Tyr's ruling and rationale, linked actions. |
| C5 | **Download original** | `GET /api/contracts/{id}/versions/{v}/original` | The original PDF or DOCX. |

## D. Overview dashboard (FR9.2, FR9.3)

| # | Component | Data | Behaviour |
|---|---|---|---|
| D1 | **Time slider** | `GET /api/dashboard?as_of=` while dragging; `POST /api/clock {sim_now}` on release; `POST /api/clock {days}` | Range from about −60 to +365 days. Quick buttons: +1 week, reset to today. Every dashboard widget refreshes. |
| D2 | **Financial exposure gauge** | `dashboard.exposure` → `{expected, worst_case, currency, contracts[]}` | Gauge (expected inside worst case) plus a per-contract table. Also show `exposure.contracts[].assumptions`. |
| D3 | **Risk heatmap** | `dashboard.heatmap.cells[] {contract_id, clause_type, month, amount}` | Toggle rows between contract and clause type. Columns are months. Cell tooltip shows the amount. Clicking a cell filters the timeline. |
| D4 | **Work-plan board** | latest `GET /api/runs` with `kind=analysis` → `workplan.workstreams[] {contract_id, status, evidence_score, reason, tasks[]}` | One card per workstream (plus "cross"), live status, evidence score bar, and the reason when the run is partial or failed. |
| D5 | **Top alerts strip** | `dashboard.alerts[]` | Top 5–10 by severity, with citation chips. |
| D6 | **Health score tiles** | `dashboard.health {contract_id: score}` | Small tile per contract. |
| D7 | **Run progress / budget bar** | `run.budget {agent_calls, tool_calls, tokens_in, tokens_out, usd, fallbacks}` | Live while a run is going; shows the limits from `/api/observability`. |

## E. Timeline (FR3)

| # | Component | Data | Behaviour |
|---|---|---|---|
| E1 | **Obligation timeline / Gantt** | `GET /api/timeline?as_of=&contract_id=` → `entries[] {id, date, due_at?, kind, title, status, amount, citation, owner}` (`due_at` is an exact UTC time when the contract states one) | Kinds: payment, renewal, notice_deadline, penalty_trigger, expiry, obligation. Status colours: past, due, upcoming, missed, done. |
| E2 | **Worst-case projection table** | `report.worst_case_projection` or timeline entries with amounts | "If no action is taken". Labelled ANALYSIS. |
| E3 | **Owner assignment** | `POST /api/owners {timeline_id, owner}` | Inline owner picker per entry. |
| E4 | **Calendar export button** | `GET /api/export/calendar.ics` | Download. |

## F. Contract graph (FR9.1)

| # | Component | Data | Behaviour |
|---|---|---|---|
| F1 | **Interactive graph canvas** | `GET /api/graph` → `nodes[] {id, type: contract/party/clause, label, …}`, `edges[] {source, target, kind, reason, severity, finding_id}` | Edge kinds: `conflicts_with` (red, animated), `depends_on` (arrow), `supersedes`, `governs`, `party_to`, `contains`. Zoom, pan, and filter by kind. |
| F2 | **Node / edge inspector** | the selected item | Contract: open detail. Clause: open the Reference Viewer. Conflict edge: open its debate thread. |
| F3 | **Cascade path highlight** | `alert.kind=cascade` | Highlight the path from the triggering contract to the dependent contracts. |
| F4 | **Legend** | static | Edge and node colours. |

## G. Agent debate panel (FR9.4)

| # | Component | Data | Behaviour |
|---|---|---|---|
| G1 | **Debate thread card (per finding)** | `GET /api/debate?contract_id=` → `findings[]` with `debate[]`, plus `rulings[]` | Loki claim and attack path, citations, then Heimdall verdicts (support/challenge/insufficient), Loki rebuttals (maintain/revise/withdraw), Tyr's ruling (winner, final severity, confidence, rationale). |
| G2 | **Live agent message stream** | `debate.messages[]` and SSE `agent_message` `{sender, receiver, kind, summary, contract_id, ts}` | Chat-style, with an agent colour and avatar. Kinds: plan, extract, clarify, timeline, attack, verify, rebut, rule, action, event, status, report, error, budget. |
| G3 | **Clarification bubbles** | messages with `kind=clarify` | Loki asks Thor; Thor answers. Pair them visually. |
| G4 | **Filters** | n/a | By contract (including `cross`), agent, kind, run. |
| G5 | **Finding severity matrix** | `findings[] {severity 1–5, likelihood 0–1}` | Scatter or 5×5 grid. Click opens the thread. |

## H. Alerts, actions and violations (FR9.5, FR6)

| # | Component | Data | Behaviour |
|---|---|---|---|
| H1 | **Prioritised alert feed** | `GET /api/alerts?as_of=&include_closed=` → `{severity, kind, title, why, due_date, citations, event_id, violation_id, status}` | Kinds: notice_deadline, payment, renewal, expiry, penalty_trigger, event, cascade. Actions: acknowledge, snooze (7 days), resolve (`POST /api/alerts/{id} {status}`). Show "why this alert". |
| H2 | **Action list** | `GET /api/actions` (sorted by priority) | Kind, contract, subject, deadline, confidence, status, needs-approval badge. |
| H3 | **Action detail / letter preview** | `GET /api/actions/{id}` → adds `counterfactual {without_action, with_action, avoided}` | Ready-to-send letter (`body_md`), recipient, citations, redlines (before/after per clause), leverage notes, and "money avoided if done". |
| H4 | **Approval controls (admin)** | `POST /api/actions/{id}/approve`, `…/reject`, `PATCH /api/actions/{id} {to, subject, body_md}` | Edit while a draft, then approve or reject. Record who and when (`approved_by`, `approved_at`). |
| H5 | **Send / apply controls (admin)** | `POST /api/actions/{id}/send` (Gmail), `…/apply` (amendment → new contract version) | Enabled only when approved. A 403 means "not approved". Show the result (Gmail message id, or the new version plus its update run). |
| H6 | **Violations table** | `GET /api/violations` | Contract, clause, breach type, breached by, exposure, status, and a "View references" button to the Reference Viewer. |
| H7 | **Exports** | `GET /api/export/actions.csv`, `POST /api/digest/draft` | CSV download; a "Draft daily digest" button creates a digest action for approval. |

## I. Events, inbox and what-if (FR5)

| # | Component | Data | Behaviour |
|---|---|---|---|
| I1 | **Inbox / event log** | `GET /api/events` | When, type, contracts, amount, status, parse method (strict/llm/manual/demo) and confidence, reject reason. Live via SSE `event` and `email`. |
| I2 | **Email format card** | `GET /api/email/template` | Copyable template for judges, plus the inbox address (`me.gmail_address`). |
| I3 | **Gmail poll status** | `GET /api/email/status`, `POST /api/email/poll-now` | Last poll time, fetched count, error. |
| I4 | **Manual event form** | `POST /api/events {subject, body, sender}` | Fallback when Gmail is down. Same parser. |
| I5 | **What-if simulator** | `POST /api/whatif {subject, body}` → `scenario_id`, `GET /api/whatif/{id}`, `DELETE /api/whatif/{id}` | Sandboxed run. Show exposure before and after, plus the scenario's alerts, violations, actions and agent messages. Discard button. |
| I6 | **Demo feed player** | `POST /api/demo/play?delay_seconds=` | Replays the scripted emails. |
| I7 | **Event impact card** | event plus related alerts and violations | "This event → these clauses → this exposure change → these actions". |

## J. Ask Odin

| # | Component | Data | Behaviour |
|---|---|---|---|
| J1 | **Q&A chat** | `POST /api/ask {question, contract_ids?}` → `{answer, citations[], insufficient_evidence, passages[]}` | Answer with citation chips. An "insufficient evidence" state when nothing verifies. |
| J2 | **Retrieved passages drawer** | `passages[] {contract_id, clause_number, score, text}` | Shows hybrid-retrieval evidence (useful for the eval team). |

## K. Reports (FR8)

| # | Component | Data | Behaviour |
|---|---|---|---|
| K1 | **Report selector + viewer** | `GET /api/reports/company`, `GET /api/reports/contract?contract_id=` (JSON, or `format=html`) | Native rendering of the JSON is preferred: executive summary, key terms, timeline, risks, actions, references, completeness (complete/partial with gaps). |
| K2 | **References section** | `report.references[] {contract_id, clause_number, quote, page, link}` | Each `link` is a viewer deep link. |
| K3 | **PDF export** | `…&format=pdf` | Download. |
| K4 | **Regenerate** | `POST /api/reports/refresh` | Run status shown on the run indicator. |
| K5 | **Counterparty risk profile** | `GET /api/insights/counterparties` | Per party: contracts, worst-case exposure, violations, late-payment events. |

## L. Observability (what exists today, NFR4)

| # | Component | Data | Behaviour |
|---|---|---|---|
| L1 | **Runs table** | `GET /api/observability → runs[]` or `GET /api/runs` | Kind (analysis/event/update/whatif/report), status, start and end, calls, tokens, USD, fallbacks, error, trace link. |
| L2 | **Run replay scrubber** | `GET /api/runs/{id}` → `messages[]`, `tool_calls[]` | Slider steps through agent-to-agent transitions in order. |
| L3 | **Per-agent cost and latency table** | `run.budget.per_agent {calls, tokens, usd, latency_ms, providers{}}` | Bar chart per agent. Shows which provider and model served each call (fallback visibility). |
| L4 | **Tool audit log** | `run.tool_calls[] {agent, tool, scope, ok, blocked, ms, summary}` | Filter by agent, tool, or blocked. |
| L5 | **Citation guard widget** | `observability.citation_guard {checked, verified, blocked, stored_citations, stored_unverified}` | "Hallucinated quotes blocked: N". |
| L6 | **Confidence calibration chart** | `GET /api/insights/calibration → buckets[] {confidence, n, verified_rate}` | Bar chart: confidence bucket against verified rate. |
| L7 | **Tool registry table** | `GET /api/tools` | Name, scope, side effect, approval needed, PII, allowed agents, argument schema. |
| L8 | **Limits and providers panel** | `observability.limits`, `observability.providers` | Read-only today; editable for super_admin later. |

---

## M. Future: tracing (LangSmith) — build the shells now, wire them later

The backend already sends LangSmith a root run per Odin run (`run_id` equals the LangSmith run id),
`run_name=<agent>:<provider>`, tags (`agent`, `provider`, `run_kind`, `whatif`) and metadata (`company_id`,
`contract_id`, `prompt_hash`, `event_id`, `sim_now`).

| # | Component | Data (expected) | Behaviour |
|---|---|---|---|
| M1 | **"Open trace" deep link** | `run.trace_url` (already returned; empty until a LangSmith key is set) | Shown on every run, agent message and action. |
| M2 | **Embedded trace tree** | LangSmith run tree (via a backend proxy endpoint to be added: `GET /api/traces/{run_id}`) | Graph nodes → agent → LLM and tool spans, with inputs and outputs, tokens, latency, and errors. |
| M3 | **Span detail drawer** | span `{name, inputs, outputs, tokens, latency, error, metadata}` | Prompt and response viewer with the prompt hash and version. |
| M4 | **Latency waterfall** | span start and end times | Critical path of a run: shows where the minutes go. |
| M5 | **Prompt version panel** | `metadata.prompt_hash` per agent | Which prompt version produced an output; diff between versions. |
| M6 | **Token and cost trend chart** | aggregated per day, agent and model | Budget burn over time. |
| M7 | **Feedback buttons** | to be added: `POST /api/feedback {run_id or span_id, score, comment}` → LangSmith feedback | Thumbs up or down plus a comment on findings, actions and answers. This feeds evals. |

## N. Future: evaluation suite (DeepEval + LangSmith datasets)

Hook: `EvalHook.record(kind, agent, inputs, output, meta)` fires on every LLM output (`kind="llm"`) and every
retrieval (`kind="retrieval"`). Expected endpoints (to be added by the eval teammate): `GET /api/evals/runs`,
`GET /api/evals/runs/{id}`, `GET /api/evals/datasets`, `POST /api/evals/run`.

| # | Component | Data (expected) | Behaviour |
|---|---|---|---|
| N1 | **Eval dashboard (scorecards)** | latest eval run → metric scores | Tiles: citation faithfulness, field extraction accuracy, hallucinated-clause rate, ambiguity-flag recall, cross-contract conflict recall, alert precision, action relevance, answer faithfulness (Ask), retrieval recall@k and MRR, latency p50/p95, cost per contract. Thresholds show pass/fail colours. |
| N2 | **Eval run history / trend** | `evals/runs[]` | Line chart of each metric over time, annotated by model, prompt version and commit. |
| N3 | **Run comparison (A/B)** | two eval run ids | Side by side per metric and per test case (for example Kimi vs MiniMax, or prompt v1 vs v2). |
| N4 | **Per-test-case drill-down** | case `{input contract or event, expected, actual, score, reason}` | Expected vs actual extraction field by field, with the metric's reason text (DeepEval gives one). |
| N5 | **Golden dataset manager** | `evals/datasets[]` | List contracts with their expected extractions, conflicts and alerts. Upload or edit goldens. Promote a production output to a golden ("mark as correct"). |
| N6 | **Retrieval eval view** | retrieval records (`dense` vs `sparse` ranks, final picks) | Per query: which clauses were retrieved and whether the right one was found. Recall@k chart. |
| N7 | **Per-agent quality table** | metrics grouped by agent | Thor, Loki, Heimdall, Tyr and Synth with their own metrics (for example Loki precision via Tyr rulings, and Heimdall challenge rate). |
| N8 | **Regression alert banner** | eval run result | Shows when a metric drops below its threshold after a change. |
| N9 | **"Run evals" button (admin)** | `POST /api/evals/run {dataset, model?, prompt_version?}` | Shows progress and links to the result. |

## O. Future: security suite (guard hooks)

Hooks: `pre_llm`, `post_llm`, `pre_tool`, `post_tool`, `on_ingest`, `on_email`. A guard raises `Blocked`; tool
calls are already audited with `blocked=true`. Expected endpoints: `GET /api/security/events`,
`GET /api/security/summary`, `GET/PUT /api/security/policies`.

| # | Component | Data (expected) | Behaviour |
|---|---|---|---|
| O1 | **Security overview** | summary counts | Blocked LLM calls, blocked tool calls, prompt injections detected (emails or contracts), PII redactions, policy violations, approvals pending. |
| O2 | **Guard event log** | `security/events[] {ts, hook, agent, tool?, rule, verdict, excerpt, run_id}` | Filters; click opens the trace (M2). |
| O3 | **Prompt-injection inspector** | the email or document flagged by `on_email` / `on_ingest` | Malicious span highlighted (demo: `corpus/samples/emails/06_prompt_injection.txt`). |
| O4 | **Quarantine queue** | blocked emails and documents | Release (admin) or delete. |
| O5 | **Tool permission matrix** | `GET /api/tools` → `allowed_agents` per tool | Agent × tool grid; side-effect and approval-gated tools marked. Editable by super_admin later. |
| O6 | **Approval audit trail** | actions with `approved_by/at`, `sent_at`, `rejected_by` plus tool_calls of `send_gmail/apply_amendment` | Who approved what, when, and what was sent. |
| O7 | **PII redaction preview** | guard output | Original vs redacted text (permission-gated). |
| O8 | **Policy settings (super_admin)** | `security/policies` | Toggle guards, thresholds, allowlists. |

## P. Future: administration

| # | Component | Behaviour |
|---|---|---|
| P1 | **User and role management** | Invite users, assign `viewer/admin/super_admin` (the backend already has `users.role` and `require_role()`). |
| P2 | **Model / provider settings** | Per-agent provider and model (today in `backend/config/odin.yaml`, for example Thor → Kimi K2.5). Show the fallback chain. |
| P3 | **Budget settings** | `max_agent_calls`, `max_usd`, `max_tokens`, `max_debate_rounds`, `max_clarify_rounds`, `evidence_threshold`. |
| P4 | **Integrations** | Gmail connection (connect or disconnect), webhook URL (Slack), LangSmith project. |

---

### Priority for the demo
1. Must have: A1–A3, B2, B4–B6, C1–C4, D1–D4, F1, G1–G2, H1–H5, I1–I5, K1–K2.
2. Should have: B9, D5, E1, G5, H6, J1, L1–L5.
3. Future: M, N, O, P (build shells with the data contracts above so wiring later is trivial).
