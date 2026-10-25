# Corpus integration contract v2

Document and external event formats follow the user's supplied specification. Runtime behavior below is an integration requirement, not a backend implementation in this repo.

## PDF structure and citations

The first extracted lines are the Key: Value cover fields. CONTRACT ID stays C01-C08, unique across the portfolio and identical in emails. The VERSION field and footer version label are omitted at the user's request. SUPERSEDES is optional and omitted for a same-ID re-upload. Dates are ISO; amounts carry INR. Top-level headings are uppercase.

```text
^(\d+(\.\d+){0,3})\s+
^(SCHEDULE|ANNEX|EXHIBIT)\s+[A-Z]
```

These are the supplied segmenter regexes. Each heading and subclause starts a new line. Examples: `3 SERVICE CREDIT`, then `3.1 For each distinct incident ...`. No printed `C01.3` prefixes are used. Footer text starts with the contract ID or Page, never a bare number. Validation rejects duplicate/spurious numeric starts from wrapped paragraphs. Schedule rows are cited `Sch A, row 1`.

Cite `{contract_id, clause_id, page, quote}` with one-based page and actual PDF text. Store the document hash with extraction state. The evaluator index uses `C01:3.1` only as a compound lookup key. Its quotes are not available to agents. Every extracted field needs source evidence, confidence and explicit uncertainty where applicable.

## Company context

Ingest inputs/company_context.md with the ten requested keys. The JSON sidecar is a structured equivalent plus canonical party IDs and baseline settings; it is not a substitute for the Markdown parser test. Risk appetite is low, base currency INR, fiscal-year start 04-01, and approval threshold INR 10,00,000. Actions strictly above INR 10,00,000 require human approval; this threshold is not authority to send other drafts automatically. Free-text priorities and dependencies are supplied for Loki/Tyr analysis.

## External email syntax

```text
Subject: [ODIN-EVENT] PAYMENT_MADE C05

EVENT_ID: EVT-DEMO-0001
EVENT_TYPE: PAYMENT_MADE
OCCURRED_AT: 2027-01-24T12:00:00Z
CONTRACT_ID: C05
COUNTERPARTY: Willow Housing Private Limited
AMOUNT: INR 60,000
REFERENCE: RENT-2027-01
DESCRIPTION:
Bank transaction BANK-DEMO-0001 cleared against January rent.
```

EVENT_TYPE and OCCURRED_AT are required. EVENT_ID is optional and must be generated/persisted if absent. CONTRACT_ID may be one ID, ALL, a comma list or UNKNOWN. COUNTERPARTY, AMOUNT, REFERENCE and SEVERITY_HINT are optional. DESCRIPTION continues to the end of the message. Optional SEVERITY_HINT is low, medium or high and is never trusted as an agent risk score. A sender calling an event SLA_BREACH does not establish liability.

Supported enum:

```text
PAYMENT_MADE, PAYMENT_LATE, PAYMENT_MISSED, INVOICE_RECEIVED,
SERVICE_OUTAGE, SLA_BREACH, DELIVERY_LATE, DELIVERY_RECEIVED,
REGULATORY_CHANGE, PRICE_CHANGE, TERMINATION_NOTICE_RECEIVED,
RENEWAL_NOTICE_RECEIVED, PARTY_CHANGE, FORCE_MAJEURE,
DISPUTE_RAISED, CUSTOM
```

inputs/emails/index.json maps each .eml and copy-ready .txt to its scenario/source record or template. Scenario-prefixed EVENT_ID values are unique across scenarios. Maintenance approvals, attestations, ordinary breach notices, early-exit requests and document-arrival observations use CUSTOM with descriptive facts; they are not mislabeled as termination notices. Parser templates cover omitted EVENT_ID, absent required fields, invalid date and invalid type. Only the last three require fallback; eventual rejection depends on the real fallback result.

Strict Key: Value parsing runs first, then bounded Groq extraction fallback with parse_confidence when required fields are missing or invalid. If fallback fails, store rejected plus reason, show it on the dashboard and auto-reply with the expected template if sending is configured. The repo linter validates authoring only and performs no LLM/API or mail operation. Gmail message IDs are runtime metadata and cannot be supplied as real IDs in these fixture files.

## Observation source records and clocks

inputs/events/*.json are internal fixture observations carrying event_id, observation event_type, occurred_at, received_at, source_ref and payload. They retain the richer facts used to author the email DESCRIPTION, with optional supersedes_event_id for corrections. They do not define additional allowed external enum values. The email index maps their local IDs to external EVENT_ID values.

For a recorded run, the trusted adapter releases only emails with received_at <= clock and only initial PDFs. Agents must not read future schedules or C08 bytes. Use occurrence times for contractual accrual, receipt for knowledge, and the contract's effective date for applicability. An accepted live email advances SimClock only if OCCURRED_AT is ahead; late mail never decrements the clock. Clock movement also triggers deadline checks without new events.

Deduplicate external EVENT_ID and Gmail message ID, then domain identities such as bank transaction and incident ID. A repeated message must not create another fee, ledger entry, transition or reply. Corrections supersede observations while preserving their audit record. Recompute affected history for late facts, preserving earlier as-known snapshots. At equal timestamps apply the released batch before checking deadlines.

C08 is received January 25 and effective February 1. Its arrival links the Aurora/Willow pair to existing C04 and C05, preserves those agreements and unrelated C02, and detects the separate C03 procurement restriction when C03 is loaded. Mark affected analysis pending until extraction and reassessment finish. The arrival email describes the document; the application ingestion path must actually provide the PDF. The full runner ZIP contains future bytes for the trusted loader, not for immediate agent ingestion.

Reset/backward travel restores documents, events, ledger and extraction visibility from the named baseline before replay. Do not retain future payments, approvals, fees or C08 knowledge. Repeated clock positions do not append duplicate daily accrual.

## Results and Gmail

Map actual agent output fields to oracle logical assertions; no particular backend response schema is imposed here. Retain workstream state, extracted fields/confidence, citations, timelines, directional money, uncertainties, transitions, rationale and approval-marked actions. Unknown remedies remain unquantified; receivables are separate from gross payables; future commitments are not counted twice. A completed analysis with unresolved terms differs from failed/incomplete processing.

runtime_specs/gmail_integration.md records authlib OAuth scopes, encrypted Fernet refresh-token storage, 15-second polling, ODIN/processed labeling, rejection replies and acceptance tests. Nothing has been connected or sent.

The only company identities are P01 Aurora Software, P02 Forge Electronics and P03 Willow Housing. Match contracts by service, invoice, order and scope as well as party IDs: Forge appears as hosting provider, application customer, component supplier and firmware vendor. C07 assigns Willow the Controller role and Aurora the Processor role. The Data Standards Board in a supplied notice is an authority reference, not a fourth contracting company.

## Fifteen-contract update

There are 15 manuscripts and 14 initially known contracts, with only C08 withheld. The three company IDs are unchanged. Context includes the 14 initial references, with no future C08 terms. DEMO-PORTFOLIO exercises the complete initial portfolio and subsequent arrival. All new observation payloads carry agreement_ref where a sender explicitly identifies the agreement; do not route on counterparty alone because each company participates in multiple independent scopes.

C09-C15 use grouped articles rather than the flat section pattern in the earlier documents. C11 includes a 2.1.1 subclause. Four older manuscripts were reordered and all evaluator citation references were remapped. Do not hardcode the old clause positions. Schedule/annex rows are extracted in displayed cell order; numeric table values carry descriptive prefixes where needed to avoid false clause starts. A project demonstration is an operational deliverable, not a dataset watermark.

Effective dates are all distinct. Several first billing periods are partial and expressly charged at the stated full fee; use the stated first due date rather than creating an overdue invoice before commencement. C10 monthly availability scoring starts with February 2027. C11 continues until milestone completion/acceptance or lawful termination. C15 coverage already earned survives the undertaking operating term. Do not treat every agreement end date as extinction of all accrued or surviving rights.

The cover keys are still uniform for ingestion, while introductions, section order, grouped numbering, wording and schedules differ. External event syntax, UTC clocks, INR arithmetic, deduplication and human-approval requirements are unchanged.
