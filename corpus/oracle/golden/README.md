# Golden dataset: agent inputs and expected outputs

This evaluator-only dataset covers six agents, 64 scenarios and 15 contracts: **384 agent/scenario vectors**, **15 Thor contract goldens**, **114 typed extraction assertions** and **276 verified citation units**. It specifies expected behavior; no actual Odin agent run or independent human review is claimed.

| Agent | Receives | Expected result |
| --- | --- | --- |
| Odin | Company context, selected documents, clock, actual agent states/results and limits | One workstream per known contract plus cross-contract work; coordination; cited scoped synthesis and actions; honest completion/stopping state |
| Thor | Raw selected PDFs, company identities, optional targeted extraction request | Normalized contractual facts, parties, dates, payments, obligations and remedies with exact quote/page/clause evidence, confidence and explicit missing/ambiguous terms |
| Norns | Actual Thor facts, clock and visible/verified history | Due/grace/cure/notice dates, past/current/future obligations, directional money and supported inaction projections |
| Loki | Actual extraction, uncertainty, timeline and related clauses | Supported attack paths, conflicts and hidden liabilities; reasoned severity/likelihood; targeted clarification when useful |
| Heimdall | Released observations, actual facts/timeline and Loki hypotheses | Event mappings, verification/challenge, idempotent state updates, corrections, noise filtering and evidence-backed alerts |
| Tyr | Actual disputes if any, verified evidence/state, contacts and approval policy | Cited rulings when needed; supported drafts/escalations with approval and confidence; unresolved issues preserved; no action execution |

## Files

- agent_goldens.jsonl: combined 384-record dataset, one agent/scenario per line, with agent, input_spec, expected_output and comparison fields. The six per-agent JSONL files contain the same records split by agent.
- JSONL companion files: thor_contract_goldens.jsonl (15 records), citation_goldens.jsonl (276), worked_examples.jsonl (36), payment_pipeline_example.jsonl (7 stages), agent_contracts.jsonl (6 roles). Original JSON files remain available for existing lookup references.
- agent_contracts.json: responsibility boundaries, input/output contracts, forbidden behavior, feedback and scoring policies.
- agent_io_matrix.csv: compact teammate handoff table.
- thor_contract_goldens.json: records keyed C01-C15, typed facts and full clause/table-row citation inventories.
- odin.jsonl, thor.jsonl, norns.jsonl, loki.jsonl, heimdall.jsonl, tyr.jsonl: 64 vectors per agent.
- citation_goldens.json: verified quote/page lookup for every citation unit.
- worked_examples.json: six scenarios expanded across all agents (36 examples), with resolved evidence and role-specific controlled upstream inputs.
- payment_pipeline_example.json: concrete input/minimum-output records through planning, all five specialist agents and final synthesis for PAY-03.
- manifest.json: counts and source hashes to detect stale answer keys.

Each vector has input_spec, expected_output and comparison. The expected exact fields are a **minimum normalized assertion subset**, not a complete backend response schema. Evidence references identify relevant grounding, not an instruction to reproduce every quote verbatim. Additional supported facts/actions are allowed within the case scope. If an agent backend uses another schema, the evaluator maps its output to the logical assertion fields first. Normalize monetary values as decimal strings without float rounding; preserve unknown null rather than converting it to zero.

## What is fixed and what is judged

Compare IDs, dates, money, party scope, event visibility and cited source identity exactly after agreed normalization. Required/forbidden findings, attack paths, reasoning, prioritization and draft wording are rubric-scored. Confidence must be agent-produced on a defined scale; it is not a hardcoded golden value. Severity and likelihood need supported rationale, not a predetermined label. A breach correctly found or an uncertainty correctly retained can pass.

Thor field assertions are deliberately minimum typed checks. The 276-unit inventory exhaustively anchors the authored numbered clauses and table rows, but it does not pretend to be an independently reviewed full legal interpretation of every sentence. A scenario-level Thor vector checks the combined stage results; use the 15 contract records for per-contract Thor calls rather than assuming a single all-document prompt. Runtime fault, budget and retry tests remain separate acceptance specifications.

## Worked payment example: PAY-03

At 2027-01-28T12:00:00Z, C05 rent is INR 100000 and the visible January 24 cleared payment is INR 60000. Thor extracts the rent, allocation and simple daily rate from C05 clauses 4.1, 5.1 and 6.1. Norns retains INR 40000 principal and computes INR 40 for each of January 26, 27 and 28: INR 120 late charge, invoice subtotal INR 40120. Loki must support its overdue-payment claim and cannot charge on the already-paid INR 60000. Heimdall maps PAY1 and applies it once. Tyr may draft an internal payment reminder/escalation with citations and human review; it must not send a notice or act as the landlord. Odin reports these as scoped invoice figures, not the complete company balance.

OUT-07 demonstrates later approval evidence: hosting recovery becomes INR 0 while the downstream credit remains INR 15000. AMB-01 preserves the unknown Schedule B fee. PROJECT-B must not mature INR 600000 from an invoice without signed acceptance. LINK-01 anticipates an equipment/service term gap without declaring a future failure already observed. DEMO-PORTFOLIO contains the 14-to-15 document transition plus scoped rent and service-credit assertions.

## Unit versus end-to-end use

For a unit test, the harness may supply the selected agent with the controlled upstream fixture from worked_examples.json. These are deliberately authored test inputs, not real agent messages. Thor gets no downstream-answer fixture. Tyr OUT-07 has an explicit injected test dispute to exercise arbitration. That does not mean the real Loki and Heimdall must disagree; no-dispute runs accept no ruling.

For an end-to-end run, supply only selected PDFs, company context, clock/configuration and observations released by received_at. Each agent receives the actual outputs of upstream agents. Never inject golden upstream state into an end-to-end demonstration or present it as live computation. The harness/evaluator may read oracle/golden; the agents must not. Do not pass an entire vector containing expected_output into an agent prompt.

C08 is unavailable before its receipt. evaluator_checkpoint_visibility records expected known IDs and released event IDs at each clock position. These records and harness_source_refs are evaluator/harness-only and must not be included in agent input. Only input_spec is the proposed agent input, populated with actual upstream results for an end-to-end run. The harness reads schedules and releases observations; agents do not get raw future event files. Checkpoints do not invent financial answers where no assertion was authored. Preserve occurrence, receipt, effective time, correction and as-known history separately.

An exact-field pass alone is not an overall pass: narrative, evidence, role boundaries and honest completion must also pass. Budget/parse failures must be reported incomplete rather than relabeled successful. Golden normal-completion expectations assume mandatory processing succeeded. No fixed agent-call count, mandatory argument or automatic external action is required.
