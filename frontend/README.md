# Odin frontend

A static Next.js / React / TypeScript frontend for the Odin agent team's REST API and SSE stream. There are **no application backend routes, Firebase SDKs, database clients, service tokens or server-side authentication handlers** in this project.

## Run the UI

```sh
npm install
npm run dev
```

Open http://127.0.0.1:3000. Without backend configuration, use **Explore demo workspace**. Preview fixtures are clearly labelled; failed live requests never fall back to fixtures. Preview can edit/approve local drafts, but cannot send email, upload documents, run agents or generate answers. The old root HTML/CSS/JS files are historical design references and are not used by Next.js.

## Connect the backend

The confirmed local backend address is `http://localhost:8000`. Copy `.env.example` to `.env.local`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=/
API_PROXY_TARGET=http://localhost:8000
```

Run `npm run dev`. The development server forwards `/api/*` and the exact `/auth/google/callback` path to the backend before frontend routes are matched. It also forwards `/openapi.json` for inspection. Sign-in/sign-up pages remain frontend routes. This is development proxy configuration, not an application backend.

Choose one frontend hostname consistently. For the existing preview, configure the agent backend:

```dotenv
FRONTEND_URL=http://127.0.0.1:3000
PUBLIC_BASE_URL=http://127.0.0.1:3000
```

Register `http://127.0.0.1:3000/auth/google/callback` as the Google OAuth redirect URI if using that origin. If you use `http://localhost:3000`, change both settings and the Google registration to that origin. After Google callback, the backend redirects to the frontend root; authenticated users are routed into the dashboard.

The backend owns the signed `session` cookie, company isolation, permissions, Gmail, uploads, PostgreSQL, agent runs and live financial/clock calculations. Its current cookie is SameSite=Lax, without Secure; it has no CSRF header requirement. Use the shared-origin proxy for the confirmed topology. Direct cross-origin calls are optional and require the backend's exact `FRONTEND_URL` CORS origin and same-site cookie behavior; separate-site deployment is not supported by the current cookie settings.

Production remains a static `out/` deployment. Configure the web server to forward `/api/*` and `/auth/google/callback` to the backend, with SSE buffering disabled and long-lived stream connections enabled. Serve all remaining application paths from the static export. `npm start` previews static files only and does not provide the development proxy. With no backend, use the explicit demo workspace.

Public variables are built into the bundle. Restart development or rebuild after changing them. Never put credentials or backend secrets in a `NEXT_PUBLIC_*` variable.

## Build and preview a static export

```sh
npm run typecheck
npm test
npm run build
npm start
```

The export is in `out/`. `npm start` serves those static files on 127.0.0.1:3000; it does not run an application backend. Deploy the export on any static host supporting directory index pages.

## API types

The backend team confirmed that OpenAPI has accurate request types, but many response types are plain dictionaries. Their `docs/api-samples/` JSON files are the source of truth for responses; those samples have not been provided to this frontend workspace yet. Known shapes have provisional interfaces and runtime checks in `src/lib/api.ts`.

When the backend is running:

```sh
npm run gen:api
```

The generator reads `OPENAPI_URL`, an absolute `NEXT_PUBLIC_API_BASE_URL/openapi.json`, or `API_PROXY_TARGET/openapi.json` and writes `src/lib/generated/backend.d.ts`. No generated schema is fabricated while the backend is unavailable. Use generated definitions for request payloads, and reconcile response interfaces with the captured samples rather than relying on OpenAPI `any` responses. Detailed route coverage and remaining contract questions are in [INTEGRATION.md](INTEGRATION.md).

## Frontend behavior

- Light/dark mode is shared across the landing page, authentication and every dashboard route. The appearance switch sits next to the landing logo, at the bottom of authentication pages, and in the dashboard sidebar. It saves `odin-theme` locally; without a saved preference, it follows the system. Switching uses an expanding color reveal where supported, with a color-fade fallback and immediate changes for reduced motion. A pre-paint script avoids a light flash on dark-mode reloads. Theme colors include graphs, heatmaps, forms and portal sheets; original PDF pages retain their paper colors.
- Shared date previews request dashboard/timeline/alerts with `as_of`; the initial date comes from `company.sim_now` and `GET /api/clock`, and any authenticated user releasing the slider posts `sim_now` to `/api/clock`. Failed commits restore the last committed date.
- SSE uses the documented `{kind,data}` envelope, 600 ms refresh debouncing, heartbeat monitoring, reconnect/offline indicators and session notifications.
- Every source-backed view has citation links and SOURCED/ANALYSIS badges. An absent provenance is explicitly unspecified; unverified citations warn rather than claim verification.
- Admin controls are hidden for non-admin users. The backend remains responsible for enforcing permissions.
- Draft editing, approval and send/apply are distinct operations. Only exact kind `amendment` uses apply; the other six confirmed kinds use send and require a recipient email. Sending/applying needs an approved action and explicit review in the UI.
- Money respects backend currency, including en-IN INR formatting; no currency conversion or live penalty calculations occur in the frontend.
- PDF.js renders originals and overlays top-left PDF-point bounding boxes using the render scale.
- Empty/loading/error/retry states are shared across API-backed views. Requests are cancelled when views change and old entity data cannot be used by a newly selected draft's controls.
- Demo-only formulas and fixtures remain in `demo-api.ts`, `demo-data.ts`, `models.ts`, and `simulation.ts`; production screens do not derive agent findings or financial projections.

## Verification limits

The backend URL is confirmed as localhost:8000, but no backend was reachable there during verification. The captured response samples and OpenAPI schema have not been supplied. Live login/OAuth, SSE, backend mutations, real document parsing and original-PDF rendering cannot be end-to-end verified yet. Current checks cover static export, TypeScript, frontend API behavior and explicit demo fixtures. Browser automation is disabled in the local Work settings.
