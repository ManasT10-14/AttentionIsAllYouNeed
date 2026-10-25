# Frontend ↔ backend contract: answers to the integration questions

Real responses captured from a seeded demo company are in **`docs/api-samples/`**. Arrays are trimmed to 3 items and long strings are cut at 400 characters. Treat those files as the source of truth for response shapes. FastAPI's OpenAPI (`/openapi.json`, or `npm run gen:api`) has accurate **request** types, but most responses are plain dicts, so OpenAPI shows them as `any`.

## 1. Base URL, envelopes
- Locally the backend runs on `http://localhost:8000`. Every API route is under `/api`. The one exception is the Google redirect URI, which is `/auth/google/callback` with no `/api` prefix.
- Envelopes are not uniform. The endpoints split like this:
  - **Bare arrays:** `/contracts`, `/alerts`, `/actions`, `/violations`, `/events`, `/runs`, `/tools`, `/insights/health`, `/insights/counterparties`.
  - **Objects:** everything else. See the sample file for each one's keys.
- `GET /email/template` returns **plain text**, not JSON.

## 2. `/api/auth/me`
- **Logged in:** `{user:{id,email,name,role}, company:{id,name,context,sim_now}, gmail_connected, gmail_address, google_configured, dev_login}`. Note that `sim_now` is inside `company`, not at the top level.
- **Logged out:** HTTP **401** with body `{"detail": {"error": "not logged in", "google_configured": bool, "dev_login": bool}}`. The flags are therefore at `body.detail.google_configured` and `body.detail.dev_login`. All other 401 responses have a plain `detail` string.

## 3. Email/password
There's no email/password login. You can sign in with Google, or with dev login (`POST /api/auth/dev-login {email, name?}`), which returns 403 when `DEV_LOGIN=false`.

## 4. OAuth, CORS, cookies, CSRF
- **OAuth flow:**
  1. The browser navigates (a full page load, not fetch) to `/api/auth/google/login`.
  2. Google redirects to `${PUBLIC_BASE_URL}/auth/google/callback`.
  3. The backend sets the session and redirects to `${FRONTEND_URL}`.
  - If a user is already logged in when the callback runs, Gmail is connected to *their* company and no new company is created.
- **CORS:** a single origin, the `FRONTEND_URL` env var (default `http://localhost:5173`). Credentials are allowed.
- **Session:** a Starlette signed cookie named `session`, with `SameSite=Lax` and not marked `Secure`.
- **CSRF:** there's no CSRF token or header.
- **Recommended:** proxy `/api` and `/auth` to `:8000` from the Vite dev server (and from the prod reverse proxy). That keeps everything on one origin, so there are no CORS or cross-site cookie problems. Example Vite config:
  ```ts
  server: { proxy: { "/api": "http://localhost:8000", "/auth": "http://localhost:8000" } }
  ```
  With the proxy in place, set `FRONTEND_URL` and `PUBLIC_BASE_URL` to the frontend's origin, and register that origin's `/auth/google/callback` in Google Cloud.

## 5. Multipart field names
These are confirmed:
- `POST /api/contracts`: field **`files`** (repeat it for each file). The query parameter `?analyze=true|false` defaults to true.
- `POST /api/company/context`: field **`file`**.
- Re-uploading a contract with the same `CONTRACT ID` on its cover page creates the next version and runs the update graph.

## 6. Clock
- **Format:** `sim_now` is an ISO date `YYYY-MM-DD`. There's no time and no timezone.
- **Reading it:** `GET /api/clock` returns `{sim_now, real_today}`.
- **Setting it:** `POST /api/clock` takes `{sim_now: "YYYY-MM-DD"}` or `{days: N}` to move it forward by N days. It returns `{sim_now}`. Any logged-in user can set it; there's no role gate.
- **SSE:** a `clock` message with `{sim_now}` is published every time the clock is set.
- **Previews:** `?as_of=YYYY-MM-DD` on `/timeline`, `/exposure`, `/heatmap`, `/dashboard` and `/alerts` is a read-only preview and does not change the clock.

## 7. Cascade paths
`GET /api/graph` now returns `cascades: {contract_id: [contract_id, ...]}`. Each entry lists the contracts hit if the key contract fails: a breadth-first walk of the `depends_on` edges, without the key contract itself. Contracts with no downstream impact are omitted. Graph node ids are `c:<contract_id>`, so the frontend's `contract_ids: string[]` option maps directly.

## 8. Heatmap type vs timeline
- Each heatmap cell has `{contract_id, clause_type, month, amount}`.
- Timeline entries have no `clause_type`, but they do have `citation.clause_number`. To get the type, join against `GET /api/contracts/{id}` → `clauses[]`, where each clause has a `number` and a `clause_type`.
- Timeline `kind` values: `payment | renewal | notice_deadline | penalty_trigger | expiry | obligation | termination_window`.

## 9. Send vs apply
Action `kind` is one of `renewal_notice | non_renewal_notice | termination_notice | breach_notice | payment_instruction | amendment | escalation_memo`.
- **apply:** only `kind === "amendment"`, the ones carrying `redlines`. It writes a new DOCX version and re-ingests it.
- **send:** every other kind. `to` must be an email address; otherwise you get a 400 asking you to edit `to`.
- Both `send` and `apply` need the action to be **approved first**, otherwise the response is 403. The flow is `POST /actions/{id}/approve`, then `/send` or `/apply`.
- `PATCH /actions/{id}` (edit) only works while `status === "draft"`.
- approve, reject, send, apply and edit require the admin role.

## 10. Citations and PDF coordinates
- **Citation fields:** `{contract_id, clause_number, quote, page, version, verified}`. `verified` is the result of the fuzzy-quote guard.
- **`bboxes` shape:** a list of `[page, x0, y0, x1, y1]`.
  - `page` is **1-indexed**.
  - Coordinates are PDF points (1/72 inch) with a **top-left origin**, the PyMuPDF convention.
  - To draw a box, scale by `viewport.scale`; y does not need flipping.
- **Rotated pages:** not handled. The generated contracts have none.
- **`pdf_url`:** returned by `/citation/resolve`. It points to `/api/contracts/{id}/versions/{v}/pdf`, which is served with cookie auth from the same origin.

## 11. SSE (`GET /api/stream`)
- **Data messages are unnamed**, so `EventSource.onmessage` receives them. (This was changed today; they used to be sent as named `odin` events.)
- **Payload:** `{kind, data}`. `kind` is one of:
  - `clock`: `{sim_now}`.
  - `agent_message`: one debate or agent bubble.
  - `run`: a run status and budget snapshot.
  - `email`: Gmail poll result.
  - **any record kind** (`alert`, `finding`, `verification`, `ruling`, `action`, `violation`, `event`, `timeline`, `report`, `dependency`, …): sent whenever that record is written. `data` is the record itself.
- Refetching the visible screen on any message, debounced at about 600 ms, is fine.
- **Pings:** a named `ping` event (`{}`) is sent every 15 seconds. It's safe to ignore.

## 12. Snooze
`POST /api/alerts/{id}` takes `{status: "snoozed", snooze_days?: int}` and defaults to 7 days.
- **Clock:** the snooze is counted from the **simulated** clock, not today's date.
- **Other statuses:** `acknowledged`, `resolved` and `open`.
- **Visibility:** `GET /alerts?include_closed=true` also returns resolved and snoozed alerts.

## 13. Downloads
- **Auth:** the PDF, original file, `.ics` calendar and CSV exports all use cookie auth. A plain `<a href>` works when the frontend and API share an origin, which the proxy in §4 gives you.
- **Cross-site deployments:** the frontend and API would need the same site plus `SameSite=None; Secure`. That setting doesn't exist yet; ask if you need it.

## Not in the API (don't call)
- `GET /api/owners` doesn't exist. Owner assignment is `POST /api/owners {timeline_id, owner}`, and the current owner shows up on each timeline entry as `owner`.
- The future screens have no endpoints yet: evals, trace tree, feedback, security quarantine and role management.
