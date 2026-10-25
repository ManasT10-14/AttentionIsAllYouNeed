# Odin corpus preparation plan

Status: corpus v2 built and locally validated after reviewing the user-supplied problem statement. See corpus/README.md and corpus/VALIDATION.md for current state.

## Confirmed in this session, 2026-10-25

- Workspace: `C:\Users\hrutu\OneDrive\Desktop\RAGNAROK`.
- Repository checkout: `AttentionIsAllYouNeed/`, branch `corpus-prep`.
- Exactly eight contract PDFs. Embed a dated amendment in one PDF; do not add a ninth contract upload.
- Start with C01-C07. Hold C08 back for the live-ingestion demonstration.
- The user will provide the authoritative Odin problem statement before generation. The handoff is interim context, not a substitute for reviewing that statement.
- No agent pipeline or UI exists in this checkout. Runtime integration and measured demo performance remain unverified.

## Proposed portfolio

The document setup above is accepted. The terms and design details below remain implementation proposals to reconcile with the problem statement.

| ID | Contract | Coverage |
| --- | --- | --- |
| C01 | Cloud hosting | SLA thresholds, maintenance exclusions, monthly credit cap |
| C02 | Customer service | Downstream service obligations linked to C01 |
| C03 | Supplier | Delivery dates, penalties, notice and cure |
| C04 | Customer supply | Delivery dependency on C03; aligned and conflicting obligations |
| C05 | Office lease | Rent, partial payment, grace period, renewal notice |
| C06 | Software subscription | Renewal, termination, missing fee schedule; embedded signed amendment with explicit effective date and limited precedence |
| C07 | Data processing | Contractual response to an explicitly fictional regulatory change |
| C08 | Partnership, initially withheld | Existing-party relationship, overlapping scope, dispute clauses, explicit independent scope rather than automatic replacement |

Use fictional entities, no official marks, and clear synthetic-document labeling. Use one currency initially, explicit calendar-day rules, a frozen scenario clock, and timezone-aware event timestamps. Final names, amounts, dates, and clauses will be set after reviewing the problem statement.

## Build sequence

1. Review the supplied problem statement and reconcile its requirements against the handoff. Record any differences before drafting.
2. Specify stable contract, party, clause, invoice, and service identifiers. Document the proposed event envelope and ingestion interface; do not imply teammate acceptance without evidence.
3. Author a pilot using C05 for payment/renewal and C01-C02 for linked obligations. Independently author evaluator expectations and boundary cases.
4. Render and inspect the pilot PDFs. Verify citation quotations and page references against the actual PDF text, and independently check dates and monetary calculations.
5. Expand to the eight PDFs after pilot checks pass. Add C06's amendment inside its PDF and C08's separate arrival scenario.
6. Validate all nine scenario families with boundary and clean controls. Keep business status separate from evaluator pass/fail. Do not force a particular number of cases or risk/control split.
7. Produce a ten-minute demo runbook using clock movement, audience-selected events, and C08 arrival. Mark actual runner integration and latency checks pending until a pipeline is available.

## Planned package

```text
corpus/
  README.md
  manifest.json
  inputs/
    company_context.json
    contracts/                 # exactly eight PDFs
    events/                    # observations, never expected answers
    scenarios/                 # initial documents, clock and event schedule
  oracle/
    expected_cases.json        # evaluator-only, independently authored
    requirement_coverage.csv
  runtime_specs/
    fault_scenarios.json        # acceptance specifications, not execution proof
  demo/
    RUNBOOK.md
```

Keep generation sources and validation intermediates outside the agent input allowlist. The ingestion manifest must enumerate only intended input files; do not recursively ingest the entire corpus directory. Support a seven-document initial manifest and explicit C08 arrival without changing the eight-document portfolio count.

## Acceptance checks

- Eight PDFs, readable text, stable clause IDs, synthetic labels, and verified citation pages.
- Coverage: renewal, payments, dependencies/conflicts, outages, fictional rule changes, dispute provisions, cure/termination, amendment precedence, and missing/ambiguous terms.
- Exact assertions for dates, IDs, currencies, and amounts; narrative rubrics for justified interpretation. No hardcoded model confidence as ground truth.
- Independent calculations, including grace/notice boundaries, partial payments, exclusions and caps. Distinguish payable exposure from recoverable credits.
- No future-event leakage: release by received time; preserve occurrence and effective dates. Include duplicate/correction and reset/replay cases.
- Amendment changes apply only within explicit scope and from their effective date; preserve historical views and unchanged clauses.
- Missing evidence remains unresolved; different jurisdictions alone do not prove a conflict. Drafted actions require human approval.
- Oracle files never enter agent context. Runtime fault and performance checks are reported as specifications until actually executed.

## Current result

The user supplied `C:\Users\hrutu\Downloads\Odin_PS.pdf`. All four pages were read and reconciled with the handoff. The eight-contract portfolio, 45 isolated scenarios, evaluator keys and integration/demo documentation are implemented. The event schema and fictional numeric terms are documented implementation defaults, not claimed teammate-approved interfaces. No agent/UI execution, independent human oracle review, commit, push, PR, or external notice has been performed.

## User format revision

The user supplied sections 3.1-3.4. All eight PDFs now use Key: Value covers, numeric clauses, uppercase headings and version 2; document labels were removed. Context includes the requested business and approval fields. External events use the exact email enum and syntax. C08 remains held back and now also seeds a second supply commitment conflicting with C03 exclusivity. Gmail/OAuth requirements are documented, with no backend implementation or external operation performed. Prior v1 files are archived under ignored work/archive-v1.

Latest user override: remove document versions. Omit VERSION from PDF covers, footer labels, document manifest entries and extraction expectations; preserve contract IDs and numeric clauses.
