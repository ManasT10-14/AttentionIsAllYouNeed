# Frontend integration map

Based on the supplied UI_COMPONENTS.md. All listed current routes are browser API calls to the configurable backend. No local API handlers remain.

| Workspace | Routes wired | Frontend behavior |
| --- | --- | --- |
| Auth & shell | /api/auth/me; /api/auth/google/login; /api/auth/dev-login; /api/auth/logout; /api/stream | Session gate, company/email/role, Google redirect, dev form only when dev_login is explicitly true, Gmail link, connection state, notifications |
| Contracts | /api/contracts; /api/contracts/{id}; /api/contracts?analyze=true; /api/demo/seed; /api/runs/analysis | Library, detail tabs, extraction/citations, warnings, health, multipart uploads, reanalysis and optional USD budget |
| Context | /api/company/context | Admin upload and parsed-field review under Admin |
| Versions | /api/contracts/{id}/diff?from=&to=; /api/contracts/{id}/lineage/{number} | Version list, red/green before-after diff, clause lineage |
| References | /api/citation/resolve; /api/contracts/{id}/versions/{v}/pdf; /api/contracts/{id}/versions/{v}/original; /api/violations/{id} | Viewer deep links, local PDF.js worker, page/zoom controls, exact clause and scaled highlights, violation details, original download |
| Overview | /api/dashboard?as_of=; /api/runs?kind=analysis; /api/clock | Backend financial values, priority alerts, health tiles, workstreams, clock preview/commit |
| Exposure | /api/dashboard?as_of= | Gauge, per-contract assumptions, contract/type/month heatmap filters, cell-to-timeline links |
| Timeline | /api/timeline?as_of=&contract_id=; /api/owners; /api/export/calendar.ics | Obligation table, status/cost/source, inline owner assignment and calendar export |
| Graph | /api/graph; /api/alerts?as_of= | Backend nodes and edges, drag/pan/zoom/minimap, search, edge filters, source inspector, debate links, optional supplied cascade paths |
| Debate | /api/debate?contract_id= | Finding threads, per-agent messages, rulings, citations, severity matrix and agent/kind/run filters |
| Alerts & actions | /api/alerts; /api/alerts/{id}; /api/actions; /api/actions/{id}; /approve; /reject; /send; /apply; /api/violations; /api/export/actions.csv; /api/digest/draft | Alert status, drafts/edit/review, financial counterfactual, redlines, separate approval/send/apply, results and exports |
| Inbox & events | /api/events; /api/email/template; /api/email/status; /api/email/poll-now; /api/demo/play | Event log, raw impact details, copyable template, polling, manual event submission and demo feed trigger |
| What-if | /api/whatif; /api/whatif/{id} | Create, inspect scenario output, refresh and discard |
| Ask | /api/ask | Questions, optional contract scope, answer/citations, insufficient evidence and passages |
| Reports | /api/reports/company; /api/reports/contract; /api/reports/refresh; /api/insights/counterparties | Native JSON sections, completeness/gaps, references, PDF export and counterparty profiles |
| Observability | /api/observability; /api/runs; /api/runs/{id}; /api/tools; /api/insights/calibration | Run selection/replay, budgets/per-agent costs/providers, tool audit filters, citation guard, calibration bars, trace links |

The frontend preserves complex unspecified records in readable field views rather than guessing their structure. Some rich presentations (full Gantt, span waterfall, detailed scenario comparisons, approval-audit visualizations) need the actual schema and remain field-based or labelled planned views.

## Planned endpoints

Evaluation, trace tree, feedback, security policy/quarantine and role-management operations are explicitly marked unavailable. The frontend does not call routes described as future in the document. Evals/Security/Admin shells show the intended sections. Security and Admin can read existing tool/configuration data; context upload already uses the current route.

## Confirmed contract — backend team reply

- Local backend: `http://localhost:8000`; application routes are under `/api`. Google callback is `/auth/google/callback`.
- Bare-array responses: contracts, alerts, actions, violations, events, runs, tools, insights/health and insights/counterparties.
- The email template response is plain text, not JSON.
- Auth: `{user:{id,email,name,role},company:{id,name,context,sim_now},gmail_connected,gmail_address,google_configured,dev_login}`.
- Logged-out auth flags are inside `401.body.detail`: `{error,google_configured,dev_login}`.
- Google and gated development email login only. There are no password endpoints.
- Cookie: Starlette `session`, SameSite=Lax, not Secure. No CSRF token/header. Use one origin via the development/production reverse proxy.
- Backend `FRONTEND_URL` and `PUBLIC_BASE_URL` must match the chosen frontend origin. Register that origin's `/auth/google/callback` in Google Cloud.
- Upload fields confirmed: repeated `files` for contracts; `file` for company context.
- `GET /api/clock` returns `{sim_now,real_today}`; `POST` accepts `{sim_now}` or `{days}` and returns `{sim_now}`. Every logged-in user may change it. Dates are YYYY-MM-DD.
- `as_of` is a read-only preview on timeline, exposure, heatmap, dashboard and alerts.
- Graph `cascades` maps raw source contract IDs to downstream contract ID arrays. Graph contract nodes use `c:<id>`. Cascade highlighting uses this map; no paths are guessed from alerts.
- Timeline clause types are joined through `entry.citation.clause_number` and the matching contract's `clauses[].number/clause_type`. Deadline kind is not treated as clause type.
- Action kinds: renewal_notice, non_renewal_notice, termination_notice, breach_notice, payment_instruction, amendment, escalation_memo. Only amendment applies; the others send. Edits require draft, delivery requires approved, all four mutations plus reject require admin. Email recipients are checked before approving/sending.
- Citation fields and top-left, one-indexed page bboxes are confirmed. Pages are not rotated in generated contracts; viewer overlays use the render scale.
- SSE data is unnamed `{kind,data}` messages, plus named ping every 15 seconds. Any non-ping record message triggers a debounced 600 ms refresh, including timeline/dependency.
- Snooze explicitly sends `{status:"snoozed",snooze_days:7}` and runs from the simulated clock. Closed-list mode includes snoozed and resolved records.
- Downloads use cookie auth and work through the shared-origin proxy.
- No GET owners endpoint exists or is called. Future evals, trace tree, feedback, quarantine and role-management operations remain unavailable.

## Remaining handoff item

Please provide the backend's **docs/api-samples/** folder. Those captured responses, rather than OpenAPI response `any` types, are the source of truth. This frontend currently uses the supplied component guide plus the confirmed answers above. Response shapes still need comparison against the actual files, especially extraction, debate/rulings, action detail/counterfactual, reports, observability and nested dashboard data.

OpenAPI remains useful for request types. `npm run gen:api` defaults to `API_PROXY_TARGET/openapi.json` when using the shared-origin frontend base.

## Integration verification

Frontend tests cover nested auth flags, company clock location, text templates, cascade ID mapping, clause joins, exact action routing, proxy paths and previous client checks. The backend was not reachable at localhost:8000 during this update, so live OAuth, SSE, parsing, mutations, downloads and PDF rendering still require a test with the backend running. No external emails were sent.

For local integration: copy .env.example to .env.local, start the backend on :8000, match both backend public URL settings to the frontend origin, then use npm run dev. For a production static export, supply equivalent proxy rules in the deployment web server.
