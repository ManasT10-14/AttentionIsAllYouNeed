# Pipeline implementation ledger

Plan: docs/superpowers/plans/2026-10-25-pipeline.md

- User authorized implementation now; no additional design approval required.
- No Git repository exists. Work in place and use a persistent ledger instead of Git-dependent skill scripts.
- Tracing and paid evaluations default off. Product decorators deferred as requested.
- Pre-flight: tasks share the typed case/execution/check/report models from task 1. Adapter evidence remains distinct from dataset references.

## Completed implementation

- Task 1 complete: typed contracts/configuration/datasets; initial 11 tests observed failing then passing. Dedicated Python 3.11.4 environment and uv.lock resolved; no global dependencies changed.
- Task 2 complete: fixture/HTTP/compiled-graph adapter seams and deterministic/security checks; 37 tests passed at that milestone.
- Task 3 complete: five actual DeepEval metric constructors verified offline, actual AnswerRelevancyMetric measured with an offline custom model, and LangSmith SDK run/feedback plumbing tested without an account upload.
- Task 4 complete: bounded async runner, timeout/error isolation, evidence gating, redacted atomic reports, CLI and exit codes. Tracing failure never changes evaluation outcomes.
- Task 5 complete: nine synthetic cases, safe/vulnerable responses, FastAPI fixture app, actual compiled LangGraph test, README and integration/metric references.

## Independent review and fixes

- Reviewer found a feedback retry/backoff stall, JSON-escaped canary false negatives, and Python boolean/number equality false positives.
- All findings reproduced in failing regression tests, then fixed: feedback attempts=1, transport retries disabled, cooperative publishing budget; raw string-leaf/key canary inspection; recursive typed JSON equality.
- Added a regression ensuring status summaries remain in safe metadata when SDK output capture is hidden.
- Full offline suite after fixes: 87 tests passed. All tests require no paid calls; external sockets are blocked.
- Safe fixture: 18 passed, 5 optional judge skips, exit 0. Vulnerable fixture: 10 failures, 8 passed, 5 optional judge skips, exit 1 (before final fixes; final commands repeated separately).
- Real local TCP HTTP smoke against the fixture server: nine cases, 18 passed, 5 optional skips, exit 0. Server was terminated afterward.
- Package wheel/sdist build and uv pip check passed; final post-fix build/check repeated before delivery.

## Decisions and limitations

- Work in place because this folder has no Git repository; no branches/worktrees/commits created.
- Exact comparisons distinguish int/float as well as booleans/numbers. A backend wanting numeric tolerance should add a dedicated comparator.
- SDK publishing budget is cooperative between requests, not forced thread cancellation; an in-flight request may exceed the remaining budget. Injected clients own their timeout/retry policy.
- Product decorators, real backend mapping, paid judge calls, and real LangSmith uploads remain unverified/deferred until backend information is available.
- Odin-specific timeline/exposure/event correctness and full threat-model coverage are future product-specific cases, not claimed complete.

## Final verification

- The documented `uv run --locked --all-extras pytest -q` initially exposed a console-entrypoint import difference for examples. Added the workspace root to pytest's pythonpath, then reran the exact command: 87 passed.
- Final safe CLI: 18 passed, 5 optional skips, exit 0. Final vulnerable CLI: 8 passed, 10 failed, 5 optional skips, exit 1.
- Final Ruff lint/format checks passed. Final wheel and source distribution rebuilt successfully. Dependency consistency check passed for 90 installed packages.
