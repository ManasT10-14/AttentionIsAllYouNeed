# Security layer implemented — 26 October 2026

## Scope and branch

Fetched `origin/integration` at `0cf510a` and merged it locally as `abca632`. The existing local configuration/documentation edits and supplied corpus were preserved. Security implementation is uncommitted. Nothing was pushed; GitHub CI remains absent.

This implements the runtime security portion S01–S06 of the earlier eval/security handoff. It preserves the official pack import, calendar/holiday/timed-event approach and email intake. It does **not** claim that the new calendar's financial/business calculations or the separate evaluation-development backlog E01–E09 have been validated or completed.

## What now happens

### 1. Tenant access and permissions

- What-if read/delete queries include the authenticated company. Foreign and unknown scenarios return the same 404 response, and deletion cannot remove another company's records even when scenario IDs match.
- Repository operations reject missing scope and attempts to override an active tenant. Run updates and workflow tool queries are also scoped.
- Event creation, email polling, what-if creation, report refresh, owner/alert changes and demo playback require admin access. Existing pack/simulation mutations already required it.
- Scenario export uses a public record-kind allowlist. It cannot export private quarantine evidence. Only the admin evidence endpoint can preview that evidence, after redaction, including owned scenario evidence.

### 2. Email and scheduled-event quarantine

- Email headers and body are inspected before strict parsing, model fallback, auto-reply, clock movement or graph launch. A malformed held message cannot reach those operations.
- The official pack's scheduled JSONL events cross the same policy when delivered. A held scheduled event pauses replay **before** advancing its clock/checkpoints or starting a graph. Repeated advance requests cannot skip the hold. Confirmed rejection or successful explicit release permits replay to continue.
- Loading a future event drop remains separate from delivering it to product agents. Oracle/reference answers are not added to prompts.
- Original held input is retained in an internal, unpublished `quarantine_evidence` record. Public event fields omit that raw content. This is application access control, not encryption at rest or a retention service.
- Review requires an admin, explanation and observed revision. Database compare-and-set claims stop two requests from launching two runs. Dismiss closes the detection while leaving input held; confirm rejects it; release validates the original source and launches once.
- A failed/interrupted release stays claimed and requires manual recovery. The normal event reassessment route cannot bypass it. Review receipts link the processing run and surface failures.

### 3. Model and output boundaries

- Checks run before every provider invocation, including tool continuations and schema repair. Structured/non-string text blocks and fragmented text are inspected too.
- Trusted system instructions remain separate. Instruction-like source spans are marked as untrusted in transient model inputs; this is recorded as detected/wrapped, without claiming proven neutralization. Stored contract text remains unchanged for citations.
- Structured model outputs receive secret redaction. If a required schema cannot safely survive the rewrite, the result is blocked instead of returning an invalid model.
- Tool tenant fields are checked recursively, and sensitive operations require a tenant context. Registry allowlists and model exclusion of side-effect tools remain in place.
- The optional classifier remains disabled by default. A sufficiently confident positive maps to the hold threshold; classifier failure is recorded as unavailable rather than clean. This policy is not a calibrated attack-accuracy claim.

### 4. One privacy policy

`eval/ragnarok/privacy.py` is the canonical recursive policy; the backend imports it through a compatibility facade. It handles sensitive dictionary keys, configured-secret literals, common credential formats, URLs, nested/fragmented content and selected PII. Normal business contact addresses remain usable.

The policy covers product JSON (including auth/company context), validation/HTTP errors, security snippets, tool audits, generated reports/exports, SSE updates, model boundaries, evaluator report exports and LangSmith payloads. Redaction runs before truncation so a clipped prefix cannot evade literal matching. Run failure diagnostics are sanitized before storage; logging avoids raw provider exceptions.

Authorized **original** PDF/source-file downloads preserve source evidence; they are not redacted replacements for the originals. Arbitrary confidential prose cannot be recognized as a credential merely by a regex.

Remote traces now default to metadata-only: inputs/outputs/serialized content are omitted, metadata/tags are allowlisted, and attachments are omitted. Set `ODIN_TRACE_CONTENT=redacted` only when intentionally enabling approved redacted-content traces. Metadata-only still provides run/agent/provider/source identifiers; it does not prove cloud upload succeeded. Existing tracing credentials were not printed or used in remote tests.

### 5. Approval and external effects

- Approval binds tenant, action revision, exact normalized tool payload, current source versions/hashes, linked finding/violation revisions and statuses, reviewer and a **one-hour real-clock expiry**. Simulated calendar time does not control approval expiry.
- Changed recipients/body, stale sources, dismissed/disputed decision basis, expiry and old status-only approvals fail closed. Old approvals must be reviewed again.
- Admin dispatch atomically claims execution and revalidates immediately before the effect. Consumed, cancelled or ambiguous claims cannot be blindly reused. A provider timeout is not treated as proof that delivery failed.
- Executing source leases are respected by contract ingestion/deletion and workspace reset. Linked finding/violation changes through repository put/status/invalidation also honor the lease, under the shared company lock. Direct trusted SQL bypasses application invariants and is not an application API.
- Amendment construction pins the approved source version/hash. Only its owning internal dispatch token can update that leased source. It creates a **local proposal/version**, without establishing counterparty consent. Reanalysis launches after execution completes; a launch failure becomes a separate warning, not a reason to apply again.
- Recipients must have documented contact/notice evidence. Free-text payment instructions are blocked because there is no typed beneficiary/amount authorization flow.
- Automatic parser replies require a matching stored strict rejection and exact parser-generated template, and receive a one-shot claim. A generic body cannot use that tool to bypass approval.
- Webhooks require explicit `ODIN_WEBHOOK_ALLOWED_HOSTS`, HTTPS and permitted alert/violation types; redirects and IP literals are disallowed. DNS pinning remains deferred.

### 6. Frontend

Security shows protected surfaces, classifier configuration, trace privacy mode, audit readability and explicit limitations. Review requires a reason, explains each decision's effect, prevents duplicate submissions, provides redacted evidence and shows the resulting run/error.

Action review shows binding, source versions, expiry and execution state. It permits editing/renewing unconsumed approvals and disables execution for missing, expired or consumed bindings. Amendments are described as local proposals. Server validation remains authoritative.

## Pack packaging repair

The fetched manifest referenced `bundle/data/holidays.csv` and `payments_ledger.csv`, but neither was tracked because the broad `data/` ignore rule excluded them. Restored the public files from the [organiser's pack](https://github.com/Nodal-leaf/Problem-Statements-RAGNAROK/tree/main/02_Ragnarok%20Odin%20The%20Contract%20War%20Room/Pack/odin_dev_pack) and added narrow ignore exceptions. Source SHA-256:

- Holidays: `46dda2b01f05660a3c0b66ea4b3f94e92dea7eeec07dc5e3720c6d078d986dce`
- Ledger: `9b64c840d5b387977114d479a5a419bc7ebe5abc651ca12158f57bc61047377b`

No answer-key data was downloaded into the product. This repairs missing inputs; it does not establish business-rule correctness.

## Verification and limits

Meaningful regressions were observed failing before fixes. Tests use synthetic secrets, disposable SQLite workspaces, mocked provider/effect boundaries and blocked external networking. Separate PostgreSQL concurrency checks use randomly named schemas with explicit schema translation and verify their tables before seeding; teardown removes those schemas. The first parity-fixture attempt incorrectly resolved public tables, creating six synthetic rows; those exact session-owned rows were removed and isolation was corrected. Existing user records were not altered by that cleanup.

The live authenticated Security page was also inspected read-only: it rendered guard status, metadata-only tracing, coverage limitations and the live tool matrix. No browser send/release/approval was performed against user data.

Local commands:

```powershell
uv sync --locked --all-extras
uv run --locked --all-extras pytest backend/tests eval/tests -q

# Optional local PostgreSQL parity; generated disposable schemas only.
$env:ODIN_SECURITY_PG_TEST = '1'
uv run --locked --all-extras pytest backend/tests/test_security_postgres.py -q
Remove-Item Env:ODIN_SECURITY_PG_TEST

cd frontend
npm test
npm run typecheck
npm run build
```

Remaining limits: broad adversarial/false-positive calibration, real provider and cloud-trace verification, full calendar/golden testing, durable worker/outbox recovery, trace/audit delivery health, retention/encryption policies, webhook DNS pinning and production deployment controls. Dev login/session settings were preserved for local use. These tests establish specific controls and regressions, not immunity to prompt injection or production certification.
