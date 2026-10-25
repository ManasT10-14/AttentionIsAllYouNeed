# Corpus v2

Exactly eight PDFs, 24 pages, 152 numbered body clauses plus two cited schedule rows, 45 isolated scenarios, and 64 email fixtures in .eml and copy-ready .txt forms. The seven-initial-plus-C08-arrival setup is preserved.

## Portfolio

| ID | Contract | Principal coverage |
| --- | --- | --- |
| C01 | Cloud hosting | SLA, maintenance evidence, credit threshold and cap, Schedule A fees |
| C02 | Customer service | Stricter downstream SLA and office-dependent support through December 31 |
| C03 | Supplier | Delivery, cure, exclusive AX-7 procurement, reasonable-time response |
| C04 | Customer supply | Delivery dependency, blank late-interest percentage, one-sided indemnity |
| C05 | Office lease | Rent, partial payments, renewal notice, initial term ending June 30 |
| C06 | Software subscription | Auto-renewal, absent Schedule B, embedded dated amendment |
| C07 | Data processing / confidentiality | Safeguards, supplied rule notices, confidentiality, compliance |
| C08 | Supply and campaign partnership | Second AX-7 procurement, conflicting convenience notice periods, independent scope and forum |

The existing eight-document allocation is retained. C08 now includes the second procurement needed for the requested supply-exclusivity trap. The user's six-document list is treated as suggested coverage, not a change to the confirmed eight-PDF limit. C07 includes confidentiality/data-processing coverage; no employment contract is added.

## Authoring and context

Each first page starts with one Key: Value per line: CONTRACT TITLE, CONTRACT ID, CONTRACT TYPE, EFFECTIVE DATE, PARTY A, PARTY B, GOVERNING LAW. Document version labels are omitted at the user's request. SUPERSEDES is optional and omitted for these agreements. Clauses use `1 HEADING` and `1.1 Text`, matching the supplied regex exactly. A trailing dot after a top-level number would not match that regex. Citation identity is `{contract_id, clause_id}`; for example C01 and 3.1, or C01 and `Sch A, row 1`. The evaluator index uses compound keys such as `C01:3.1`; these are not printed clause prefixes.

company_context.md contains all ten requested keys. The JSON sidecar holds equivalent parsed values, stable party IDs and the frozen timeline configuration. Approval threshold is INR 10,00,000; actions above it require human approval. Existing scenario action drafts remain marked for review even below that threshold.

Baseline: 2027-01-15 09:00 UTC with C01-C07. C08 is received on January 25 and effective February 1. Scenarios that initially include C08 start January 25. C06 amendment is known at baseline but effective March 1. Monetary comparisons use INR decimal arithmetic; all scenario times use UTC calendar rules. These are reproducible corpus defaults.

## Events and evaluation

The external feed is the exact `[ODIN-EVENT] TYPE CONTRACT_ID` email syntax in INTERFACE.md. All 16 event enums have templates. Scenario email records carry raw observations without expected risk or liability answers. SEVERITY_HINT is shown only as an untrusted sender assertion in the SLA_BREACH template. Internal JSON files are fixture source records for the trusted replay adapter, not a replacement external email schema.

Reset between the 45 scenarios; do not concatenate their event streams. Each event schedule stays outside agent context until its received_at. C08 bytes stay unavailable until the live-arrival event. The normal scenario families are supplemented by arrival and one-sided-indemnity review. Six TRAP cases cover reasonable time, blank percentage, internal contradiction, procurement exclusivity, lease/support continuity, and one-sided indemnity. Existing outage and jurisdiction cases cover the other requested conflicts.

The evaluator alone reads oracle/expected_cases.json, expected_terms.json, evidence_index.json, seeded_traps.json and coverage files. PASS means supported expected behavior, including correctly detected breach or preserved uncertainty. Business status is scoped to the case, not the whole loaded portfolio. Unknown money is null. Model confidence is required but never hardcoded as an expected constant. No file here claims that Odin has passed.

## Distribution

Run tools/package_corpus.py for ZIPs under RAGNAROK/deliverables:

- odin-initial-upload-v2.zip: seven PDFs, company context, initial manifest; no future events or C08.
- odin-live-arrival-v2.zip: C08, receipt observation and its copy-ready email. The application must release the document through ingestion; an email alone is not assumed to upload PDF bytes.
- odin-runner-inputs-v2.zip: full inputs, emails and manifest for the trusted loader; includes future assets requiring visibility enforcement.
- odin-evaluator-only-v2.zip: answer keys, coverage, runtime/Gmail acceptance specifications and validation record. Never ingest into agents.

All 24 PDF pages were rendered and visually inspected. Numeric segmentation, metadata, citations, contexts, event enums, selected arithmetic and deterministic PDF rebuilding pass local checks. Gmail/OAuth, Groq fallback, labels, rejection replies, real agent runs and dashboard integration are not implemented or tested in this corpus repository. See VALIDATION.md and runtime_specs/gmail_integration.md.
