# Odin corpus preparation handoff

> Prepared: 2026-10-25
>
> Repository: https://github.com/ManasT10-14/AttentionIsAllYouNeed
>
> Branch: `corpus-prep` (`corpus prep` was requested; Git disallows spaces)
>
> Session summary: Plan an eight-contract synthetic corpus, expected test outcomes, and an interactive ten-minute demonstration of Odin.

## Goal

Prepare a synthetic contract portfolio and business-event fixtures for Odin, a multi-agent contract intelligence system. The corpus must support citation-grounded extraction, timeline simulation, cross-contract analysis, event-driven reassessment, challenges between agents, and actionable reports. Supply independent evaluator-only answer keys. Demonstrate genuine responses to audience-selected inputs instead of displaying predetermined outputs.

The user belongs to a four-person team: one member owns agents, one owns evaluations, one owns UI, and this user owns corpus/document generation. Earlier discussion incorrectly interpreted this role as final-report generation; the user clarified that the immediate task is generating the input corpus and test cases.

## Current state

**Confirmed:**

- The problem statement was read in full: four pages, local source listed below.
- The teammate's SynthDoc reference was inspected read-only. It is a procurement-document generator for a different problem statement.
- The user explicitly requested planning before implementation.
- The user considers eight contracts sufficient and wants all six scenario families identified in the PS plus three additional families.
- A test "passes" when the system behaves as expected. It does not mean the business relationship is compliant or risk-free.
- The demo target is approximately ten minutes with about three showcased scenarios.
- Dynamic contract arrival and audience interaction were discussed; detailed designs remain proposals.
- The GitHub repository was empty when inspected. This handoff is the only authored project artifact in this session.

**Not implemented or verified:**

- No contracts, amendments, events, oracles, generators, agent implementations, dashboards, or demo runners have been created.
- No agent/UI/evaluation integration or performance measurement has occurred.
- Dates, amounts, fictional companies, event schema, starting clock, and exact portfolio contents have not been agreed with teammates.
- No software failure has been diagnosed in Odin; no Odin source code was present in the remote repository at inspection.

The instruction to create and push this handoff authorizes this documentation task. It does not by itself authorize starting corpus generation; resume by reviewing the plan and remaining interface decisions.

## Files in play

These source paths are local to the originating Windows machine. They have not been uploaded into this repository.

| File or directory | Why it matters |
| --- | --- |
| `C:\Users\abdul\Downloads\Odin_PS.pdf` | Authoritative four-page problem statement; all FR/NFR requirements |
| `C:\Users\abdul\Downloads\SynthDoc\generate.py` | Reference generation and packaging workflow |
| `C:\Users\abdul\Downloads\SynthDoc\core\fault_injector.py` | Reference defect catalog and test-oracle construction |
| `C:\Users\abdul\Downloads\SynthDoc\core\json_generator.py` | Reference structured feeds; includes artificial OCR confidence values |
| `C:\Users\abdul\Downloads\SynthDoc\core\packager.py` | Reference packaging and domain-specific procurement checks |
| `C:\Users\abdul\Downloads\SynthDoc\core\rasterizer.py` | Optional scan generation using PyMuPDF and Pillow |
| `C:\Users\abdul\Downloads\SynthDoc\templates\helpers.py` | Reference document drawing helpers; watermark function inspected was a no-op |
| `C:\Users\abdul\.codex\RTK.md` | Instructions supplied through the user's AGENTS.md context; command-output handling |
| `HANDOFF.md` | This briefing; intentionally committed because the user explicitly requested pushing a handoff |

Local checkout: `C:\Users\abdul\Documents\Codex VS\AttentionIsAllYouNeed`.

## Problem statement requirements to preserve

Odin is more than a single-call contract summarizer. It accepts company context and multiple contracts, builds per-contract and cross-contract workstreams, and continuously updates its findings against time and events.

| Component | Required behavior |
| --- | --- |
| Odin / FR1 | Plan, delegate, track workstreams, coordinate clarification/debate, and trigger synthesis |
| Thor / FR2 | Extract parties, terms, dates, payments, obligations, penalties, compliance, and termination; attach confidence and exact clause evidence; flag uncertainty; support targeted re-extraction |
| Norns / FR3 | Track past/current/future obligations, support simulated time, and project inaction with supported financial exposure |
| Loki / FR4 | Adversarial review, cross-contract conflicts, reasoned attack paths, severity/likelihood, and clarification requests to Thor |
| Heimdall / FR5 | Map events to contracts/clauses, reassess exposure, verify or challenge Loki, and filter severity-rated alerts |
| Tyr / FR6 | Resolve disputes with rationale; draft cited notices/amendments/memos; indicate human approval and confidence |
| Workflow / FR7 | Real feedback loops with configurable iteration, evidence, and budget stopping conditions |
| Synthesis / FR8 | Per-contract reports and company report: conflicts, exposure, prioritized actions, worst-case projection, and references |
| Dashboard / FR9 | Contract graph, time slider, exposure gauge/heatmap, debate view, alerts, and drafted actions |

NFRs require separate agent responsibilities and explicit messages/state, grounded facts distinguished from analysis, honest uncertainty/completion status, graceful failures, bounded loops/retries/cost, observability, no redundant whole-document rereads, reproducibility, and meaningful LLM participation.

The corpus supports testing these requirements; documents alone cannot prove runtime architecture, bounded retries, loop termination, performance, or UI behavior. Those need an actual runner and acceptance checks.

## Scope and proposed portfolio

**User constraint: eight contracts.** Contract count is separate from scenario/test count: reuse the same portfolio with different event sequences and clock checkpoints.

The following allocation was proposed, not finalized:

| ID | Document | Principal coverage |
| --- | --- | --- |
| C01 | Cloud hosting agreement | SLA, outages, exclusions, credits, caps |
| C02 | Customer service agreement | Downstream service commitment dependent on C01 |
| C03 | Supplier agreement | Delivery, penalties, cure periods |
| C04 | Customer supply agreement | Delivery commitment dependent on C03 |
| C05 | Office lease | Rent, late payments, renewal, valid notice delivery |
| C06 | Software subscription | Auto-renewal, termination, ambiguous/missing referenced fee |
| C07 | Data-processing agreement | Compliance obligations and supplied fictional regulatory-change events |
| C08 | Partnership agreement | Dispute provisions, jurisdiction, overlapping commitments |

An amendment attachment was suggested for precedence testing. Clarify whether eight counts base agreements or all separately uploaded legal documents. Do not quietly grow the corpus beyond the user's constraint.

For dynamic-arrival testing, an alternative is to load seven of the eight initially and hold one back for live ingestion. Decide which document and its relationship before authoring; do not assume that a partnership agreement automatically functions as an amendment. Audience-edited versions should be tracked as explicit experimental versions, not silently added as extra baseline contracts.

## Scenario families and meaning of pass

The six families identified from the PS and three proposed additions are:

| # | Family | Example assertions |
| --- | --- | --- |
| 1 | Renewal windows | Compute notice cutoff; distinguish timely valid notice from a missed window |
| 2 | Payments and penalties | Track full/partial payments and grace periods; calculate only contract-supported charges |
| 3 | Cross-contract conflicts/dependencies | Connect both sides with evidence; recognize both incompatible and aligned obligations |
| 4 | Outages | Apply SLA thresholds, exclusions, service credits, and caps |
| 5 | Regulatory changes | Reassess an affected contractual obligation using a supplied fictional rule/event and effective date |
| 6 | Jurisdiction/dispute provisions | Identify relevant incompatibility requiring review; different jurisdictions alone do not establish invalidity or a conflict |
| 7 | Termination and cure | Check notice, cure window, remedy evidence, and whether termination is supported |
| 8 | Amendments and precedence | Apply explicit changes from their effective date; preserve unchanged terms and historical state |
| 9 | Ambiguous or missing terms | Preserve uncertainty, request targeted evidence, and avoid invented terms/amounts |

An initial proposal was two variants per family (18 cases) covering risk and clean/control conditions. The user corrected the definition of "pass"; do not misrepresent 18 cases or a mandatory 9/9 split as a finalized requirement.

For every case distinguish:

- **Business status:** compliant, at risk, breached, or unresolved.
- **Test status:** pass/fail based on whether Odin produced the expected supported behavior.

A breach correctly detected is a passing test. An ambiguous clause correctly left unresolved is also a passing test. Include clean/control inputs to measure false alarms, without redefining pass as compliance.

Each evaluator-only case should state expected fields and evidence, required and forbidden findings, time checkpoints, event mappings, exposure formulas/currencies, expected actions or no-action outcome, clarification needs, approval requirements, and completion state. Use exact comparison for IDs/dates/amounts and rubrics for valid narrative explanations. Agent confidence is not an objectively known constant to hardcode into the oracle.

## Heimdall corpus design

Provide a simulated stream of business events, not live external integrations for the initial demo. Input events state observations; they must not contain the answer such as the expected risk severity, affected clause, or liability calculation.

Proposed event attributes, subject to agent-team agreement:

- `event_id`, `event_type`, `occurred_at`, `received_at`.
- Entity/service/invoice references sufficient for contract matching.
- Type-specific payload such as outage duration, paid amount/currency, or approval evidence.
- Source record/reference, and correction or supersession links where applicable.

Release an event only when its received time is reached. Distinguish occurrence, receipt, and contractual effective dates. A clock advance must also trigger deadline checks when no business event arrives.

Illustrative scenario only, not an authored contract: a credit of INR 10,000 for an outage exceeding 60 consecutive minutes, excluding maintenance approved at least 48 hours earlier, capped at INR 20,000 per month. Test 45/60/90-minute outages, missing versus present approval evidence, unrelated vendors, duplicates, and the third qualifying outage in a month. Distinguish a provider's credit liability from the company's recoverable credit; do not automatically add credits owed to the company to its payable exposure.

For debate coverage, Loki may propose exposure and Heimdall may find exclusion evidence; Tyr resolves a genuine disagreement. Do not fabricate agent disagreement solely for presentation. Also test later evidence confirming an earlier risk.

## New agreement during an active timeline

The user specifically asked about introducing another agreement between parties that already share a contract.

Do not automatically replace the existing agreement. Classify with evidence:

1. Independent scope: retain both sets of obligations.
2. Explicit amendment: update only changed terms.
3. Explicit replacement: apply from the stated effective date, preserving history and surviving obligations.
4. Unclear or conflicting overlap: flag uncertainty and use clarification/arbitration.

Expected workflow: extract the newcomer, link canonical parties and referenced agreements, inspect precedence and scope, recompute affected timelines/dependencies, reassess alerts and events, update reports, and retain the audit history. Unrelated contracts keep their state. Mark affected analysis pending while the update is incomplete.

Record uploaded/received time separately from effective time. Historical views must distinguish what was contractually applicable from what the system knew then. Example dates previously discussed were illustrative, not accepted corpus facts.

## Interactive ten-minute demo proposal

Concern raised by the user: fixed contracts plus a fixed simulation could look like fixed outputs. Keep a reproducible baseline but let judges choose meaningful runtime inputs.

Prioritize these controls:

| Control | Audience choice | Visible recomputation |
| --- | --- | --- |
| Clock | Date before/at/after a deadline | Obligations, renewals, penalties, alerts |
| Event submission | Vendor, duration, payment amount, occurrence/receipt date, evidence | Clause mapping, conditions/exclusions, exposure, action |
| Agreement ingestion (optional) | Upload or edit a prepared agreement/amendment before submission | Extraction, relationship, precedence, timelines/conflicts |
| Reset | Restore the named baseline | Fresh comparable experiment without stale events or accumulated penalties |

Show the submitted input, quoted evidence, actual agent findings/transitions, before/after state, and completion/pending status. Unchanged document extraction may be reused; clearly distinguish persisted results from new computation. Neither display canned outputs as live results nor expose evaluator-only oracles to agents.

Suggested schedule: 0-2 minutes portfolio/baseline; 2-4 judge-selected clock movement; 4-7 judge-created event plus a changed value; 7-9 optional agreement ingestion or cross-contract result; 9-10 updated company report and buffer. If ingestion is not ready, keep the third segment within the supported clock/event controls. Three scripted storylines previously proposed were renewal, payment, and outage with downstream exposure; selection remains open.

Backward time travel must restore/replay from a baseline with appropriate event visibility, not merely decrement the displayed date while retaining future state. Use real measured execution times to set scope. A clearly labeled saved run can be a fallback for API failure, not a substitute passed off as live execution.

## Reference findings and what has been tried

No corpus implementation was attempted. Read-only discovery established:

- `generate.py:57`: `generate_single_bidder(bidder, tender, output_base, create_zip=True, dpi=200, scan_realism=True, progress_callback=None)` bundles generated PDFs and structured files. Reuse the concept of a scenario package, not bidder logic.
- `core/fault_injector.py:27`: `DEFECT_CATALOG`; `:328`: `apply_faults_to_bidder(...)`; `:593`: `build_test_oracle(...)`. Useful patterns for explicit planted conditions and assertions.
- `core/rasterizer.py:13`: `pdf_to_images(pdf_path, output_dir, dpi=200, add_scan_realism=False, format="jpg")`. Optional robustness variants, not a required first step.
- Reference answer keys and agent-visible material share a directory; avoid this leakage. Its oracle derives labels from its own compliance evaluation; Odin expectations should be independently authored/reviewed.
- Reference code uses `date.today()`, current timestamps, and unseeded randomness. Freeze scenario time and seed variation.
- Reference OCR confidences are artificial constants, not measured OCR accuracy.
- Government certificates, portal verification, procurement eligibility scoring, and official logos are irrelevant to Odin's contract task.

Environment probes on the originating machine:

- `import pymupdf` failed: `ModuleNotFoundError: No module named 'pymupdf'`.
- PDF extraction succeeded with `pypdf.PdfReader`; the PS has four pages.
- `import reportlab` failed: `ModuleNotFoundError: No module named 'reportlab'`.
- No packages were installed. Recheck the actual implementation environment before selecting dependencies; no renderer was validated.

Earlier scope corrections to preserve: the user's role is corpus generation, not just final-report formatting; the earlier 24-scenario proposal is superseded by the smaller eight-contract approach; all numeric demo examples remain illustrative.

## Current best approach

Agree on shared interfaces, author a small pilot with independent expected outcomes, validate it end to end, and only then expand to the full eight-contract portfolio. A fixed corpus and variable events/clock support both reproducible evaluations and live audience interaction. Favor a small generator and standard structured files over copying the unrelated SynthDoc application or building an extra server.

Proposed future layout, not present files:

```text
corpus/
  README.md
  manifest.json
  inputs/
    company_context.json
    contracts/
    events/
    scenarios/
  oracle/
    expected_cases.json
    requirement_coverage.csv
  runtime_specs/
    fault_scenarios.json
```

The ingest path must use an explicit allowlist/manifest containing only `inputs/`. Keep internal canonical source text for PDF validation separate from evaluator annotations; do not accidentally bypass extraction in an extraction test.

## Next steps

1. Read this briefing and obtain the authoritative PS if working on another machine. The local PDF and SynthDoc sources are not in Git.
2. Review proposed scope with the user; do not treat assistant-proposed terms or schemas as approved facts. Confirm whether the eight-document limit includes amendments and which document is held back for live arrival.
3. Align with the agent teammate on accepted PDF/text formats, stable party/contract/clause IDs, citation structure, event envelope, simulated-clock API/semantics, live ingestion, incremental invalidation, and reset/replay.
4. Align with the evaluation teammate on expected-output schema, required/forbidden findings, independent financial/date calculations, narrative rubrics, and input/oracle isolation. Specify runtime fault tests separately.
5. Align with the UI teammate on event/clock/reset controls, pending/error states, live evidence/debate display, and before/after exposure.
6. After generation is authorized, draft pilot fixtures: one straightforward contract, one late-payment/penalty case, and one linked-contract case. Freeze fictional identities, clock/timezone, currency handling, calendars, and source IDs. Add exact boundary and clean/control variants.
7. Validate citations against final rendered PDF text and pages, verify monetary/date calculations independently, and run the pilot through the real agent pipeline. Confirm no oracle leaks and no invented clauses/amounts.
8. Expand to eight contracts with coverage across all nine families. Reconcile overlaps rather than forcing one document per family. Use explicit applicable fictional regulatory events rather than implying real legal advice.
9. Add runtime specifications for API retries, malformed documents/events, loop limits, budget exhaustion, deduplication, honest incomplete state, and structured trace/replay. Execution proof belongs to the runner, not the corpus alone.
10. Rehearse three demo interactions with audience-chosen values. Measure end-to-end latency, verify baseline reset, and produce a short runbook plus a clearly labeled fallback recording or saved run.

## Key constraints and context

- Plan first; do not silently proceed from this handoff into full implementation.
- Eight contracts, about three live scenarios, approximately ten minutes. Document count is not test-case count.
- A successful test means expected system behavior, including correctly found risk or correctly preserved uncertainty.
- No forced resolution of ambiguity, automatic supersession based on matching parties, fabricated money, or aggregation across currencies without supplied conversion assumptions.
- Preserve history, event ordering/visibility, duplicate handling, evidence lineage, pending state, and human approval for draft actions.
- Corpus preparation does not authorize sending drafted legal/business notices or other external communications.
- No PR creation or merge was requested. Push this documentation to `corpus-prep` only.
- This handoff is intentionally versioned at the user's request, overriding the handoff skill's usual scratch-file convention.
