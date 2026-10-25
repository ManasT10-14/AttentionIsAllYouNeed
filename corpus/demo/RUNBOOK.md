# Ten-minute live demonstration

Status: rehearsal plan only. No live Odin run, measured latency or fallback recording has been produced. Use actual agent results; the oracle is for evaluation staff and must not be loaded or displayed as a live answer.

## Prepare

1. Load company context and all contracts except C08 using the initial-upload package. Verify C08 is absent from the initial graph. Fix the initial clock at 2027-01-15 09:00 UTC.
2. Verify extraction cites the actual PDF pages. Test reset/replay and received-time filtering with PAY-07 and ARR-01 before the demonstration.
3. Set visible loop, call, and budget limits in the real runner. Show pending and error states. Measure complete ingestion and each interaction; shorten the demonstration if responses exceed the time budget.
4. Keep answer keys in the evaluator environment only. A labeled recording may be prepared after a real rehearsal, but none is included in this corpus.

## Three interactions

| Minutes | Interaction | Evidence to inspect |
| --- | --- | --- |
| 0-2 | Explain Aurora Software, Forge Electronics and Willow Housing, and show the fourteen-document portfolio. Show one completed extraction and workstream status. | Actual C01/C02 clauses, graph dependency, agent trace |
| 2-4 | Reset into the C05 payment scenario. Let the audience choose a cleared amount from INR 0-100000 on Jan 24, then move to Jan 25, Jan 26, and Jan 28. | C05:4.1-C05:5.1; principal and started-date fees recomputed, not incremented repeatedly |
| 4-7 | Reset to C01/C02. Let the audience choose 30, 45, 60 or 90 outage minutes, then choose a maintenance approval record or withhold it. Submit the actual [ODIN-EVENT] email from its copy-ready .txt file after editing the chosen observation. | C01:3.1-C01:6.1 and C02:5.1-C02:2.1; distinct receivable/payable directions, uncertainty and genuine agent verification |
| 7-9 | Reset to the fourteen-document baseline. Advance to Jan 25 and submit C08, then to Feb 1. | C08 linked to C04/C05 through Aurora and Willow; existing agreements and unrelated C02 retained; C03 exclusive-procurement conflict, pending-to-complete extraction, receipt versus effect |
| 9-10 | Show the updated report, prioritized actions, evidence and human-approval markings. | Actual synthesis, completion state, transitions and measured latency |

If ingestion is not implemented, replace the third interaction with the C05 renewal cutoff: May 31 at 16:59:59, 17:00:00 and 17:00:01 UTC, using a valid or wrong-address receipt. Explain that live arrival is pending. A full-portfolio clock movement will also affect other rent/payment obligations; use isolated scenarios when demonstrating a single calculation, and label the scope.

Audience-selected payloads are new experimental runs. Save the chosen input, clock, configuration and trace with a new run ID; do not silently overwrite the baseline or add a ninth baseline PDF. Repeating a clock position must not add another day's charge. Real disagreement may lead to Tyr arbitration; do not force agents to disagree for presentation.

## Failure and reset

On API or parse failure show incomplete/pending state, the retry budget and the last successful state. Never substitute a canned oracle response. If a real saved run is used, label it as saved. Reset the clock, documents, observations, ledgers, extraction state and scenario configuration together, while retaining the previous run as audit history.

Use the v2 packages and inputs/company_context.md. Gmail integration behavior and unimplemented acceptance checks are in runtime_specs/gmail_integration.md. Do not claim that corpus email files demonstrate a working poller or rejection auto-reply.

## Current full-portfolio rehearsal

Start DEMO-PORTFOLIO with its 14 baseline PDFs, then release the four observations in receipt order. Jan 16: outage; Jan 20: timely hosting-credit claim; Jan 24: INR 60000 cleared rent payment; Jan 25: C08 arrival. At Jan 28 the January rent has INR 40000 principal and INR 120 late charge. At Feb 1 that invoice late charge is INR 280; preserve INR 10000 hosting receivable separately from INR 15000 application credit payable. These selected amounts are not the entire company balance. Show the C03/C08 procurement conflict and all 15 contract workstreams after arrival.

For additional judge interaction choose HIRE, PROJECT, MAINT, NDA, RECOVERY or WARRANTY variants. A delayed return attestation is not disclosure evidence; a missed response window is not proof of an incurred repair cost; an unsigned milestone is not itself a late demonstration. Show the actual clause, record, calculation and unresolved status as appropriate. LINK-01 and LINK-02 demonstrate future continuity gaps without claiming an already observed service failure.
