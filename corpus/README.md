# Odin: fifteen-contract corpus

For each agent's inputs and expected outputs, start with the evaluator-only [golden dataset guide](oracle/golden/README.md) and `oracle/golden/agent_io_matrix.csv`. It contains 384 agent/scenario vectors, 15 Thor extraction records, 36 worked examples and a payment pipeline example. Only the harness/evaluator may read answer keys; end-to-end agent inputs use actual upstream results.

The active portfolio contains exactly **15 PDF contracts across three companies**, with **15 tables, 15 distinct effective dates, 64 scenarios and 94 email fixtures**. Document versions and fictional-data labels remain absent. The initial upload contains 14 contracts; C08 is introduced during live arrival.

## Companies

| ID | Company | Sector |
| --- | --- | --- |
| P01 | Aurora Software Private Limited | Software; focal company |
| P02 | Forge Electronics Private Limited | Electronics and device infrastructure |
| P03 | Willow Housing Private Limited | Housing and property operations |

Eight agreements pair Aurora with Forge; seven pair Aurora with Willow. No fourth contracting company or self-contract is introduced. The Data Standards Board is an event-source authority, not a contracting company.

## Portfolio and drafting forms

| ID | Agreement / form | Counterparty | Effective date |
| --- | --- | --- | --- |
| C01 | Hosting services undertaking | Forge | 2026-12-15 |
| C02 | Customer commercial letter | Forge | 2027-01-01 |
| C03 | Purchase-order conditions | Forge | 2027-01-05 |
| C04 | Sales-order acceptance | Willow | 2027-01-08 |
| C05 | Office lease deed | Willow | 2027-01-03 |
| C06 | Firmware subscription order | Forge | 2027-01-10 |
| C07 | Resident-data processing instructions | Willow | 2027-01-12 |
| C08 | Smart-building project framework | Willow | 2027-02-01 |
| C09 | Backup-equipment hire deed | Forge | 2027-01-04 |
| C10 | Resident portal SaaS order | Willow | 2027-01-07 |
| C11 | Milestone statement of work | Forge | 2027-01-09 |
| C12 | Emergency maintenance work order | Willow | 2027-01-11 |
| C13 | Mutual engineering confidentiality undertaking | Forge | 2026-12-20 |
| C14 | Resident-service recovery schedule | Willow | 2027-01-13 |
| C15 | Manufacturer warranty undertaking | Forge | 2027-01-14 |

The writing differs as well as the graphic treatment. Openings include recitals, an order confirmation, a commercial letter, an undertaking, a project mandate, a work authorisation and a warranty grant. C02, C05, C07 and C08 have reordered operative sections with remapped citations. New manuscripts use grouped subclauses and C11 includes a deeper 2.1.1 clause. Purchase/order forms lead with commercial tables; other documents put their schedules or annexes after the operative terms. Confidentiality, assignment, compliance, indemnity and exit drafting have been adapted to their subject matter rather than copied as one identical closing block.

The seven ingestion cover keys and numeric clause convention stay consistent because the supplied segmenter requires them. Printed numbers match `^(\d+(\.\d+){0,3})\s+`; top-level headings are uppercase. Tables use stable row references such as `Sch A, row 1` or `Annex A, row 1`. Clauses and rows are verified against the final PDF page text. The portfolio currently contains 43 pages, 230 numbered body clauses and 46 cited table rows.

## Failure consequences and planted issues

The documents define different triggers, remedies and limits: capped delivery charges; simple late-rent charges after grace; combined equipment hand-back charges; percentage service credits; milestone-delay charges; approved-cost reimbursement; disclosure damages requiring evidence; and replacement-delay charges. Cure and termination routes remain separate from automatic monetary accrual. Missing values and uncertain notice terms remain unresolved rather than filled with guesses.

Planted issues include upstream delivery after a downstream commitment, stricter downstream SLA thresholds, exclusive sourcing versus an alternate purchase, incompatible notice periods in one framework, a joint-forum question, an office lease shorter than its dependent service, hosting expiry before application-service expiry, and backup-node hire ending before recovery support. Different jurisdictions alone are a control, not proof that a contract is invalid.

Evaluator-only `oracle/conflict_matrix.csv` identifies eight issues with evidence and cases. `oracle/remedy_catalog.json` records the consequence for every contract, including conditions where no numeric fee can be invented. Twelve seeded-trap entries include proof/uncertainty controls. These files are not agent inputs.

## Context, events and scenarios

`inputs/company_context.md` supplies the ten requested company-context keys; its JSON sidecar contains the three-company registry and the 14 initially known contract references. It does not reveal the withheld C08 document or its terms before receipt. The baseline is 2027-01-15 09:00 UTC. C08 is received January 25 and effective February 1; scenarios initially containing C08 start January 25.

`inputs/scenarios/index.json` lists 64 runs. Reset between alternatives. The DEMO-PORTFOLIO run loads all 14 initial documents, releases C08, and combines an outage, a timely hosting claim and partial rent payment. Its exact assertions cover selected obligations, not the complete company balance. Other runs isolate boundary, control, ambiguity, penalty and conflict conditions across every contract.

All 16 external event types have templates. There are 94 .eml fixtures and matching copy-ready .txt files: 74 scenario observations plus 20 type/parser fixtures. Scenario descriptions contain observations, not expected risk severity or liability calculations. The internal JSON records support trusted replay; only released emails and selected PDFs belong in agent context. Use received_at for visibility, occurred_at for business effects and the contract effective date for applicability.

## Distribution and limits

Run the eight commands in the root README. Company browsing copies are in `company_contracts/Aurora_Software`, `company_contracts/Forge_Electronics` and `company_contracts/Willow_Housing` (15, 8 and 7 agreements). Shared contracts appear in both signatories' folders; the canonical portfolio still has 15 unique agreements. These full-portfolio copies include C08 and must not be used as the initial upload.

ZIPs appear under Desktop RAGNAROK/deliverables:

- `odin-initial-upload-v2.zip`: 14 PDFs, company context and initial manifest; no future events or C08.
- `odin-live-arrival-v2.zip`: C08 and the receipt observation/email.
- `odin-runner-inputs-v2.zip`: all 15 PDFs, event assets and manifest for the trusted loader; visibility enforcement is required.
- `odin-evaluator-only-v2.zip`: answer keys, conflict/remedy catalogs, coverage, runtime specifications and validation record. Never ingest into agents.

PASS means supported expected behavior, including correctly found breach or preserved uncertainty. The 64 cases are authored expectations, not passing Odin runs. Confidence is required from agents but not prescribed as an exact constant. Independent human review and real agent/UI/Gmail integration remain pending. No mail or business notice has been sent. See VALIDATION.md for checks performed and INTERFACE.md for the external email contract.
