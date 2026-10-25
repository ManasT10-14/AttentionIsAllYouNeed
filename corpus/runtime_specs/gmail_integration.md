# Gmail/OAuth implementation contract

These requirements come from the user-supplied integration specification. This repository supplies documents, event emails and acceptance cases; it does not contain a Gmail poller, OAuth server, LLM fallback or email-sending implementation. No account has been connected and no mail has been sent.

## Authentication

- Use Google OAuth through `authlib` for the logged-in company account.
- Request `openid`, `email`, `profile`, `https://www.googleapis.com/auth/gmail.readonly`, and `https://www.googleapis.com/auth/gmail.modify`. Restrict application use of modify to labels. Add `https://www.googleapis.com/auth/gmail.send` only if the rejection auto-reply is retained.
- Store refresh tokens encrypted with Fernet; take the encryption key from an environment variable. Do not commit tokens or keys or put them into prompts, logs, fixtures or the corpus manifest. Persist token updates atomically and identify records by the authenticated company account.
- Configure the Google Cloud consent project in Testing and allow the company account to authorize it. Judges only send email to the company inbox; they do not log into this application and need not be OAuth test users.
- Real client IDs, secrets, callback URL, Fernet key and company-account consent must be configured in the application environment by the application owner. No credentials are supplied in this corpus.

## Polling and deduplication

Poll every 15 seconds with users.messages.list and query:

```text
subject:"[ODIN-EVENT]" -label:ODIN/processed
```

Fetch matching messages and confirm the subject actually starts with `[ODIN-EVENT]` before parsing. Parse the subject as `[ODIN-EVENT] <EVENT_TYPE> <CONTRACT_ID|ALL>`; comma-separated IDs and UNKNOWN are supported as documented in INTERFACE.md. A Pub/Sub push adapter is a stretch goal.

Deduplicate on EVENT_ID when provided and on Gmail message ID in every case. If EVENT_ID is absent, generate and persist one linked to the Gmail ID. A retry of the same Gmail message must not produce a new ID, another ledger mutation or another auto-reply. The test fixtures use scenario-prefixed EVENT_ID values to avoid collisions between independent runs; bank transaction and incident identities still require domain deduplication.

Persist the terminal processing outcome and apply Gmail label `ODIN/processed` after handling. Keep parsed/accepted and rejected statuses distinguishable in shared state. Handle pagination, transient polling failures and label retry without losing deduplication state. These are acceptance requirements, not verified behavior here.

## Parse, clock and rejection

1. Apply a strict Key: Value parser to the header, ending at `DESCRIPTION:`; all subsequent lines are free text. EVENT_TYPE and OCCURRED_AT are required. Validate the enum, timezone-bearing ISO timestamp and subject/body consistency.
2. If required fields are absent or parsing fails, request LLM extraction fallback using the configured Groq model and record its parse_confidence and evidence. Bound calls/retries; do not replace an unparseable time with the current time or silently accept an unsupported type.
3. If fallback also fails, persist status=rejected and a reason, show it in the dashboard, and send a template-only auto-reply if that feature and scope are configured. Never send raw contract text, tokens or unrelated inbox content back to a sender.
4. For an accepted event, if OCCURRED_AT is ahead of SimClock, advance the clock and recompute. A late observation must not move the clock backward. Preserve actual receipt and occurrence times for history and corrections.
5. SEVERITY_HINT is an optional sender allegation. It is not a verified risk score, expected answer or basis to bypass contract evidence. The same applies to an event called SLA_BREACH: Heimdall must verify it.

For prerecorded scenarios, the runner must stage each email at its recorded received_at; never deliver all future emails at once. The internal JSON observations are fixture source records, not the external Gmail parser enum. The .eml files implement the requested external syntax.

## Rejection response template

```text
Subject: Re: <original subject>

We could not process this Odin event: <short parse reason>.
Please resend using this template:

Subject: [ODIN-EVENT] CUSTOM UNKNOWN

EVENT_ID: <optional unique event ID>
EVENT_TYPE: <one supported event type>
OCCURRED_AT: <ISO 8601 timestamp with timezone>
CONTRACT_ID: <contract ID, comma list, ALL or UNKNOWN>
COUNTERPARTY: <optional counterparty>
AMOUNT: <optional amount with currency>
REFERENCE: <optional invoice or incident reference>
SEVERITY_HINT: <optional low, medium or high>
DESCRIPTION:
<observations and supporting references>
```

The response is a parser aid, not a contract notice or agent risk finding. The corpus includes no code that sends it.

## Acceptance runs for the application teammate

| Input | Expected application behavior |
| --- | --- |
| Each of the 16 templates | Accept type and retain subject/body evidence |
| UNKNOWN or ALL and comma lists | Infer affected scope using actual evidence; preserve unresolved matching |
| parser/NO_EVENT_ID | Generate one stable persisted ID for its Gmail message |
| parser/MISSING_KEYS | Attempt bounded extraction fallback; accepted only on supported required fields |
| parser/INVALID_DATE or INVALID_TYPE | Attempt bounded fallback, otherwise store rejected with a reason and optional template reply |
| Duplicate Gmail message or repeated EVENT_ID | No duplicate transition, fee or reply |
| PAYMENT_MADE with same bank transaction in distinct messages | No duplicate cleared-payment credit |
| SLA_BREACH with SEVERITY_HINT=high and only 45 minutes | Verify C01/C02 thresholds independently; do not trust the hint |
| Future OCCURRED_AT | Advance SimClock; recompute deadline state |
| Late receipt or correction | Keep clock monotonic, recompute affected history and retain earlier as-known view |

The strict fixture linter in scripts/corpus/build_emails.py verifies authoring only. It is not proof that the application fallback, OAuth, polling, encryption, labels, dashboard or auto-replies work.
