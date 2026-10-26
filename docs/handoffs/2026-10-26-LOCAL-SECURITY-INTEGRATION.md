# Local instance and security integration — 26 October 2026

The tested local application is the merge base for this integration. Commit `f1d4ed6` preserves its manual-event rejection/retry handling, Events-to-Simulation navigation, event dates, Norns evidence serialization, and official bundle CSV repair. The incoming security implementation is `origin/integration` at `9fdd810`.

The merge incorporates tenant and role enforcement, delivery-time scheduled-event quarantine, private quarantine evidence and revision-aware review, canonical privacy redaction, metadata-only tracing, bound/expiring approvals and single-use execution claims, source/basis leases, and the Security/Actions UI. Existing branch document assets remain separate from the active official-pack runtime.

Integration adjustments:

- Retained the local `/data/` ignore rule and event fixes while resolving the merge.
- Updated the manual-intake test identity to satisfy the incoming admin requirement.
- Added the checkout's `eval/` directory to the Windows launch script's Python path so the backend loads this checkout's canonical privacy module, including when using an existing environment.
- Fixed a live performance regression in recursive privacy redaction. The three saved checkpoints contained about 1.69 MB of JSON and triggered 41,818 environment scans, taking about 24.9 seconds and timing out navigation/session requests. A fresh environment-secret snapshot is now taken once per redaction boundary and reused through recursion. The same payload took about 0.9 seconds with one scan. A regression verifies redaction, non-mutation, one scan per boundary, and visibility of changed environment secrets on the next call. No redaction rules were removed.

Verification after integration:

- 230 backend/shared-privacy tests passed. Two PostgreSQL cases skipped in that default run were run separately and both passed using disposable, schema-isolated fixtures and sandbox effects.
- All 80 frontend tests and TypeScript checking passed.
- Next.js local production build passed for all 22 routes.
- Browser navigation passed across all 16 dashboard pages without browser exceptions or failed API responses; Events search and the existing 19-record replay workspace remained readable.
- A fresh synthetic workspace verified `security-v2`, active guards, metadata-only traces, input quarantine before graph execution, public/evidence secret redaction, foreign-tenant evidence denial, required review explanations, and confirmation/rejection without starting agents.
- The existing local PostgreSQL endpoint remains configured through the ignored local environment file. Docker publishes it on loopback.

The earlier 18-event live replay and three checkpoint records were retained. This integration did not repeat that entire paid model replay; scheduled-event holds and resumption have focused regression coverage. No real email send, real approval execution, Google login, cloud-trace delivery, or adversarial-calibration certification is claimed. Evaluator/oracle answer files were not read.
