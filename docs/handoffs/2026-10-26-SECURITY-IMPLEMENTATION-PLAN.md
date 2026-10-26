# Security implementation plan

**Goal:** implement the security requirements S01–S06 from the approved handoff against integration `0cf510a`, including official pack simulation ingress. The user's request to build that handoff authorizes implementation; no new product direction or evaluation rebuild is proposed.

**Architecture:** extend existing guard/hooks, tenant-scoped repositories, transactional review and tool approvals. Keep canonical evidence unchanged; sanitize model/remote observability representations. Email remains an event source alongside the official pack's timed events. Use existing Python/FastAPI/SQLAlchemy and React components.

**Constraints:** preserve local configuration changes and corpus; no CI, push, paid models or real outbound effects in tests. Do not assume the calendar's business calculations are validated. No oracle in product context. Use temporary databases and synthetic canaries.

## Work and ownership

- [ ] Guard/privacy: shared recursive secret policy, model continuation/repair and output boundaries, truthful detected/wrapped decisions, nested tenant argument checks; regression tests first. Own security/guard.py, new core/privacy.py, core/telemetry.py, llm/call.py and focused tests.
- [ ] Quarantine: stop email before parsing/reply/clock/run, subject/header coverage, atomic review with reason and dismiss separate from release; security UI and tests. Own services/events.py, api/quality.py, security review service, security-view.tsx and focused tests.
- [ ] Approval: bind tool/payload/source revision, expiry and atomic one-shot execution, deny stale/replayed approvals, redact tool audits, constrain system replies; tests. Own tools/registry.py, tools/core.py, new approval service, action routes section only and focused tests.
- [ ] Tenant/simulation integration (coordinator): close scenario read/delete hole, require roles for mutation routes, scoped repository operations; route scheduled pack events through guard before clock/model effects. Add coverage/status API and accurate UI details after reviewing worker changes.
- [ ] Review combined changes and run backend/eval/frontend suites and typecheck. Record unresolved limitations rather than advertise complete prevention.

## Review focus

1. Foreign/missing scenario indistinguishable; owner's records remain unchanged.
2. Held malformed input causes no model, reply, clock movement or event graph.
3. Tool results in subsequent model turns and non-string blocks receive checks without corrupting normal structured outputs.
4. Split/nested synthetic credentials never reach mocked trace, audit or incident sinks.
5. Two release/send requests cause at most one launch/effect; errors do not silently permit replay.

Each owner writes a focused regression, observes it fail for the intended reason, implements the fix, then reruns the focused suite. The coordinator runs the full suites after integration. No implementation commits are requested.
