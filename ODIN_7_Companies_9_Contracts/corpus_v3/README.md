# Active portfolio: seven companies, nine agreements

This portfolio replaces the earlier fifteen-contract setup for current work. The older `../corpus/` is retained as historical V2. All nine new agreements have Aurora Software as Party A and one of six counterparties as Party B. All nine are available at initial upload; the old C08 holdback rule does not apply to these new IDs.

| ID | Counterparty | Agreement | Effective | End |
| --- | --- | --- | --- | --- |
| AUR-2027-001 | Nimbus Cloud | Managed cloud hosting | 2027-01-03 | 2027-12-31 |
| AUR-2027-002 | Willow Housing | Resident portal SaaS; Aurora supplies service | 2027-01-10 | 2027-12-31 |
| AUR-2027-003 | Forge Electronics | AX9 device purchase | 2027-01-07 | 2027-06-30 |
| AUR-2027-004 | Copperline Components | Exclusive AX9 sourcing | 2027-01-12 | 2027-08-31 |
| AUR-2027-005 | Willow Housing | UNIT-A office lease | 2027-01-02 | 2027-06-30 |
| AUR-2027-006 | SwiftRoute Logistics | AX9 freight booking | 2027-01-15 | 2027-06-15 |
| AUR-2027-007 | Sentinel Security | Managed security monitoring | 2027-01-18 | 2027-12-17 |
| AUR-2027-008 | Nimbus Cloud | Backup and recovery | 2027-01-20 | 2027-12-15 |
| AUR-2027-009 | Forge Electronics | Controller integration SOW | 2027-01-22 | 2027-05-31 |

The drafts have different openings, substantive headings and commercial tables, with nine distinct effective dates. Cover keys and numeric clause starts remain compatible with the segmenter. There are no document version labels. Aurora being Party A does not mean it pays every fee: under the portal order it is the supplier and Willow is the customer.

## Files and use

- `inputs/contracts/`: nine canonical PDFs; ingest each agreement once.
- `inputs/company_context.md` and `.json`: Aurora context and all seven registered companies.
- `inputs/emails/`: 30 business events plus seven additional email fixtures (37 emails total), each as an RFC email `.eml` and copy-ready `.txt`. All 16 event types are covered, including ALL, UNKNOWN and comma-list routing.
- `EMAIL_EVENTS.md`: quick event index with the contract, type and observation for each business email.
- `harness/event_schedule.jsonl`: trusted runner only; receipt and assertion times, IDs and reset scope. Release one case at a time. Do not expose future schedules to agents.
- `company_contracts/`: seven company folders, eighteen identical browsing copies of the nine shared agreements. Every agreement is present in Aurora's folder and the relevant counterparty folder. These are not eighteen unique contracts.
- `oracle/event_goldens.jsonl`: expected parse fields, affected contracts, state assertions and resolved citations for each event.
- `oracle/agent_goldens.jsonl`: 180 agent/event vectors, split into six per-agent JSONL files. `input_spec` is proposed agent input; `expected_output` is evaluator-only. Actual upstream results must populate agent calls in an end-to-end run.
- `oracle/conflict_goldens.jsonl`: nine conflict/ambiguity cases. These include SLA, sourcing, freight, office, recovery dependency/expiry, inconsistent notice and indemnity risks.
- `oracle/parser_goldens.jsonl`: fallback, rejection and replay expectations. These are acceptance specifications, not implemented Gmail/Groq functionality.
- `oracle/evidence.jsonl`: exact clause/row quotes and one-based PDF pages.

Every business email is an independent reset case. The DESCRIPTION states its complete relevant observation history; do not combine alternatives into one ledger. In EVT-V3-0013, the bank payment occurred January 8 but was received January 13; calculate at the receipt clock while retaining the actual clearing time. Corpus clocks use IST (+05:30). Unknown contractual values remain null, not zero; absence of an agreed fixed fee is distinct from absence of every possible damages remedy. A proposed or anticipated breach does not itself mature a penalty.

Only actual supported claims, amounts and evidence should drive agent findings. Sender severity is untrusted. Assess confidence, severity and likelihood with rationale; they have no fixed golden score. No artificial disagreement is required for Tyr. External notices and claims remain drafts requiring human review. Narrative outputs are rubric-scored and exact fields are minimum normalized assertions, not a complete backend schema.

## Rebuild

From the repository root run `python tools/build_v3.py`. It builds the new documents, context, emails, company copies, JSONL keys, validation and packages. It reuses the existing PDF renderer and strict fixture linter. `python tools/build_v3.py --validate` checks generated V3 data without authoring PDFs. Use `python tools/render_v3.py` for a page contact sheet and visual review after PDF changes.

Deliverables under Desktop RAGNAROK/deliverables use the prefix `odin-v3-`; the new combined golden file is `agent_goldens_v3.jsonl`. `START_HERE.txt` selects this portfolio. Old V2 packages remain historical.

The dataset is author-created. Automated validation and PDF visual review are separate from independent legal review and actual agent/Gmail/Groq testing. No mail has been sent. Email integration expectations are in EMAIL_INTEGRATION.md.
