# Heimdall email interface - new portfolio

These are fixture and application acceptance requirements. This repository does not implement or claim a running Gmail poller, Groq fallback, OAuth flow, dashboard or auto-reply service. No messages have been sent.

Send messages to the logged-in company's Gmail account. The fixture recipient `odin-inbox@aurora.example` must be replaced with that actual inbox; `.example` addresses are reserved placeholders. Importing `.eml` files is optional; the paired `.txt` provides subject and body for copy/paste. Contract IDs must remain unchanged.

Subject: `[ODIN-EVENT] <EVENT_TYPE> <CONTRACT_ID|ALL>`

```text
EVENT_ID: EVT-V3-0001
EVENT_TYPE: INVOICE_RECEIVED
OCCURRED_AT: 2027-02-01T10:00:00+05:30
CONTRACT_ID: AUR-2027-001
COUNTERPARTY: Nimbus Cloud Private Limited
AMOUNT: INR 2,00,000
REFERENCE: NIM-JAN-01
DESCRIPTION:
January hosting invoice received; no payment or overdue allegation yet.
```

EVENT_TYPE and OCCURRED_AT are required. EVENT_ID is optional, with a stable ID generated if absent. CONTRACT_ID supports an actual ID, ALL, comma-separated IDs or UNKNOWN. COUNTERPARTY, AMOUNT, REFERENCE and SEVERITY_HINT are optional. Everything after DESCRIPTION: is free text through end of mail. SEVERITY_HINT is a sender allegation, not a finding. An amount is an observation, not automatically a penalty or claim.

Enum: PAYMENT_MADE, PAYMENT_LATE, PAYMENT_MISSED, INVOICE_RECEIVED, SERVICE_OUTAGE, SLA_BREACH, DELIVERY_LATE, DELIVERY_RECEIVED, REGULATORY_CHANGE, PRICE_CHANGE, TERMINATION_NOTICE_RECEIVED, RENEWAL_NOTICE_RECEIVED, PARTY_CHANGE, FORCE_MAJEURE, DISPUTE_RAISED, CUSTOM.

Poll every 15 seconds with `users.messages.list`, query `subject:"[ODIN-EVENT]" -label:ODIN/processed`, follow pagination and confirm the actual subject prefix. Strict key:value parsing comes first. When required fields are missing or invalid, use bounded Groq extraction with parse_confidence and supporting text. Revalidate the extracted enum, timezone-bearing ISO timestamp and subject/body scope. Do not invent a time, counterparty or contract to force acceptance.

If extraction still fails, store status=rejected with a reason, show the reason in the dashboard, and auto-reply with the expected template if gmail.send and that feature are configured. Dedupe on EVENT_ID and Gmail message ID before applying any mutation or replying. If EVENT_ID is absent, persist its generated value against the Gmail message ID so retries do not create new events. Label handled messages ODIN/processed after durable terminal outcome, including rejected records, so they do not loop. Separate event identity from domain identities such as bank transaction or restore request; different events can still describe one real incident.

Advance SimClock to OCCURRED_AT only when it is ahead. Late receipts never move the clock backward; recompute affected history while retaining the earlier as-known view. The trusted schedule stages receipt times. Each business case resets and supplies its own observations; these cases are alternative runs, not one cumulative event stream.

Use Google OAuth through authlib with openid, email, profile, gmail.readonly and gmail.modify (modify used for labels). Add gmail.send only for configured auto-replies. Encrypt refresh tokens with Fernet using an environment key; never commit tokens/credentials. The company account authorizes in the Testing project; judges only send messages. Actual inbox, OAuth credentials and encryption keys belong in application configuration.

## Rejection auto-reply template

```text
We could not process this Odin event: <short reason>.
Please resend using:
Subject: [ODIN-EVENT] CUSTOM UNKNOWN
EVENT_ID: <optional unique ID>
EVENT_TYPE: <supported enum>
OCCURRED_AT: <ISO timestamp with timezone>
CONTRACT_ID: <ID, comma list, ALL or UNKNOWN>
COUNTERPARTY: <optional>
AMOUNT: <optional amount with currency>
REFERENCE: <optional>
SEVERITY_HINT: <optional low|medium|high>
DESCRIPTION:
<observations>
```

Parser and replay cases in oracle/parser_goldens.jsonl specify acceptance expectations; conditional fallback success is not asserted as an observed run. Rejection replies must not include contract text, credentials or unrelated inbox data.
