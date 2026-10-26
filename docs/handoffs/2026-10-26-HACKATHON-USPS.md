# Odin: USP shortlist and demo strategy

Prepared 26 October 2026 for **1–2 remaining development days**. These are recommendations after reviewing the problem statement, current `integration` code, the active nine-contract portfolio, and the prior live website audit. They are proposed capabilities, not features claimed to have been implemented or verified.

## The recommendation in one minute

**Make Odin the system that discovers where a business promise is unprotected, tells you the last safe moment to act, and proves why its proposed action is justified.**

For the demo, build one strong workflow:

1. Reveal a supplier/customer protection gap that a single-contract reviewer would miss.
2. Show the action deadline that closes the gap before the company loses its options.
3. Open a short, source-backed decision receipt with the disagreement, calculation, uncertainty and human decision.

Use the existing graph, time controls, debate, actions, workflow and report diff. Improve how those pieces answer one business question. Do not spend the remaining time adding several disconnected pages.

First fix misleading money, missing-evidence passes, tenant access and unsafe processing. A sophisticated demonstration with wrong debtor or penalty arithmetic is weaker than a smaller correct one. The companion [Claude handoff](C:/Users/offic/OneDrive/Desktop/Ragnarok/docs/handoffs/2026-10-26-EVAL-SECURITY-CLAUDE-HANDOFF.md) explains those requirements.

## What would actually distinguish the demo

The PS already asks for agents, citations, a graph, a clock, worst-case exposure, debate, event monitoring and drafted actions. Those are requirements, not extra USPs. The pulled branch already has most of those surfaces, plus redlines, workflow reports/diffs, runtime security events and live scores. Do not pitch their mere presence as a new invention.

Commercial systems also advertise agentic review, obligation tracking, analytics and contract workflows: see [Ironclad](https://ironcladapp.com/product/ai-based-contract-management/) and [Icertis](https://www.icertis.com/products/platform/). This is a limited public feature comparison, not a full competitive audit. It means “we have AI agents and renewal reminders” is a weak differentiation claim. The more distinctive angle is a visible, testable connection between **multiple promises, conditions, time, uncertainty, money and safe action**.

No feature guarantees a win. Scores below are my engineering/product judgments about this PS and this repo, not survey results or probabilities of winning.

## Ranked shortlist

Ratings weight practical usefulness 40%, fit to the PS 20%, distinctiveness of the demonstration 20%, and feasibility using this repo in 48 hours 20%. Priority also considers dependencies. Effort assumes an experienced developer and corrected underlying calculations; estimates are deliberately ranges.

| Priority | Feature in simple words | Rating /10 | Smallest useful demo slice | Rough extra effort | Decision |
|---|---|---:|---|---|---|
| 1 | **Promise protection gap:** what we promise customers but cannot recover from suppliers | **9.7** | Hosting vs portal outage rules, two clauses, one money comparison | 4–7 h | Build the main story |
| 2 | **Last safe moment:** when you must start acting, not merely when a contract ends | **9.5** | One prerequisite chain plus deadline/owner/evidence | 4–7 h | Best second feature if time remains |
| 3 | **Proof before payment:** do not call money due until required proof exists | **9.4** | Invoice + delivery/acceptance gate for one payment | 4–7 h | Excellent alternate second feature |
| 4 | **Ask one useful question:** resolve the uncertainty that changes the decision | **9.2** | One branch-changing missing fact with two outcomes | 3–5 h | Low-cost differentiator |
| 5 | **Decision receipt:** a compact, inspectable explanation of the action | **9.1** | Link existing debate, clause, amount, clock, eval and approval | 2–4 h | Add as shared presentation layer |
| 6 | **Smallest repair:** the fewest changes that resolve a chain of conflicting promises | **9.0** | Compare lease extension with relocation consent | 6–10 h | Stretch; narrow to fixed options |
| 7 | **Claim rescue:** stop an earned credit disappearing through a missed claim window | **8.9** | One conditional claim packet and countdown | 4–6 h | Strong alternative, depends on #2 |
| 8 | **Two clocks:** what happened versus when we learned about it | **8.9** | Late bank confirmation replay with two timestamps | 5–9 h | High technical value; data-model work |
| 9 | **Show what breaks the answer:** test boundaries instead of showing only a happy path | **8.8** | 30/31 and 120/121 minute outage comparison | 3–5 h | Excellent evidence for judges |
| 10 | **No double counting:** distinguish what we owe, might owe, and may recover | **8.7** | Money waterfall for one incident with provenance | 4–7 h | Correctness foundation; avoid ROI exaggeration |
| 11 | **Safe action rehearsal:** preview consequences before approving a notice or amendment | **8.6** | Compare one draft against current state without applying | 5–9 h | Build on existing what-if/redlines |
| 12 | **Security decision replay:** show the attack, the blocked capability and zero side effects | **8.5** | Synthetic poisoned email sandbox + linked guard result | 3–5 h after fixes | Short closing moment, not main product |
| 13 | **Consent is a dependency:** a new document cannot silently remove an old obligation | **8.4** | Relocation proposal requiring Willow's written consent | 3–5 h | Useful within #3/#6/#11 |
| 14 | **Show the cost of waiting:** compare today's feasible action with tomorrow's lost option | **8.3** | One claim/notice window with bounded scenario values | 4–6 h | Use only supported values |
| 15 | **Find one fix that protects several contracts** | **8.2** | Shared PROD-AUR dependency and affected obligations | 5–8 h | Good graph extension |
| 16 | **Memory without contamination:** reuse what is still valid and explain what changed | **8.1** | Clause change → only affected findings rerun | 5–9 h | Useful performance proof |
| 17 | **Missing document radar:** show what cannot be established from this portfolio | **8.0** | Required acceptance/consent referenced but absent | 3–5 h | Cheap if framed as evidence gap |
| 18 | **Notice validity check:** correct recipient, channel, delivery time and attachment | **8.0** | Ready-to-send gate for one notice with exact source | 4–6 h | Valuable action-safety polish |
| 19 | **Portable dispute packet:** give a human a usable incident evidence bundle | **7.9** | Sources + timeline + amount + disagreement + draft | 3–5 h | Reuse exports; fix source links first |
| 20 | **Risk-based attention queue:** rank decisions by urgency, evidence and consequence | **7.8** | Three actions with “why first” | 3–5 h | Prefer clear policy over opaque score |
| 21 | **Contract stress lab:** sweep outage duration/delivery dates and map rule changes | **7.7** | Deterministic sliders for one scenario | 6–10 h | Larger #9, defer if unreliable |
| 22 | **Negotiation pack:** propose a supported amendment to close a measured gap | **7.5** | Add maintenance exclusion to customer clause, before/after | 6–10 h | Requires careful draft/accepted distinction |

These hours are incremental feature slices, not a promise to ship all of them in the remaining time. Shared prerequisites can dominate. A broad legal reasoning engine, general optimizer or new enterprise connector cannot honestly be built in a few hours.

## Detailed top ideas, with example workflows

### 1. Promise protection gap — “We promised more than we bought.”

**Simple meaning:** show where Aurora's obligation to a customer is stricter than the protection it receives from a supplier. This connects legal language to a business vulnerability before anything goes wrong.

**Real corpus example:** Nimbus hosting AUR-2027-001 §4.1 grants a credit for a continuous unplanned outage **over 120 minutes** and excludes properly notified approved maintenance. Willow portal AUR-2027-002 §4.1 gives Willow a credit for customer-visible outage **over 30 minutes**, without the same planned-maintenance exclusion. The portal runs on PROD-AUR.

**Workflow:**

1. Open “Protection gaps” from the dashboard.
2. See `Nimbus hosting → PROD-AUR → Willow portal` with the two exact clauses side by side.
3. Enter a **45-minute customer-visible approved maintenance** event, with supplier notice/exclusion requirements satisfied. The comparison shows no Nimbus incident credit, but a potential Willow credit of **5% × ₹120,000 = ₹6,000** if its claim conditions are met.
4. Open the gap explanation: the supplier complied, yet Aurora may still owe the customer a credit.
5. Review mitigations: negotiate aligned maintenance treatment, obtain a customer maintenance agreement, or change operational arrangements. Every choice remains a proposal requiring the right parties' agreement.

**What judges see:** the system detects a loss pathway that reading either contract alone misses. It connects the PS's cross-contract, event and timeline requirements to one understandable consequence.

**Backend delta:** typed dependency identity, source-linked threshold/exclusion/claim rules, affected-contract traversal and deterministic comparison. Current event mapping searches named contracts first; a generic cascade alert is insufficient. The dependent contract's actual remedy must be evaluated too.

**Frontend delta:** one gap card showing “promise / protection / uncovered condition / proposed fix,” a two-clause comparison and the existing focused graph. Highlight only the relevant nodes; do not present a hairball of every clause.

**Guardrail:** ₹6,000 is a conditional customer credit, not an automatically paid cash fine. For a qualifying 180-minute unplanned incident, Nimbus's potential ₹20,000 credit and Willow's potential ₹6,000 credit are separate contracts/claim processes. Do not automatically net them into “₹14,000 profit” or authorize setoff.

**Completion check:** 30/31 and 120/121 minute boundaries, approved-maintenance exclusion, claim window and duplicate event tests. Thresholds come from extraction with source verification, never from hard-coded demo output.

### 2. Last safe moment — “A June expiry can require a decision much earlier.”

**Simple meaning:** calculate backward from a breach or lost right, taking into account required notice, approvals, evidence and lead times. A deadline list tells you when the end occurs; this tells you when action must begin.

**Example:** Aurora promises a staffed UNIT-A support desk throughout the customer order until **31 December 2027**, while the separate office lease ends **30 June 2027**. Relocation needs Willow's written consent. A June 30 warning alone is too late to be useful if consent, negotiation or an extension requires time.

**Workflow:**

1. Select the UNIT-A dependency warning.
2. See the chain: current lease expiry → either extension or relocation consent → continued staffed desk obligation.
3. Enter a clearly labelled company planning assumption, such as “allow 10 business days for internal review.” Use actual contractual notice/consent periods where specified. Unknown counterparty turnaround stays unknown.
4. Odin presents a latest planning start date or range, with “contract requirement” and “our planning assumption” visibly distinct.
5. Assign an owner and evidence needed: signed extension or written relocation consent. A calendar reminder does not mark the gap resolved.
6. Move the clock and see a feasible option become at risk, with a draft escalation for human review.

**Why memorable:** it anticipates loss of options, not just a due date. It gives the time slider a purpose.

**Backend delta:** explicit prerequisite graph, reverse date arithmetic with timezone/business/calendar day types and uncertainty. Persist contractual deadlines separately from assumed operational lead times. Use a conservative range when required facts are missing.

**Frontend delta:** “Act by” card, prerequisite checklist, owner, source and assumption labels; show the actual obligation end separately.

**Guardrail:** do not claim a legally exact start date if the agreement gives no response period. Say “planning deadline under these assumptions.” Do not change the source contract because an internal owner clicked complete.

### 3. Proof before payment — “An invoice does not prove the money is due.”

**Simple meaning:** an obligation becomes due only after its actual conditions are satisfied. Show exactly which proof is missing.

**Example:** the Forge device agreement has a balance payment tied to both a valid invoice and signed acceptance. The integration SOW has milestone-dependent payments. The current timeline fallback can use the effective date when it lacks a first due date; that can create a payment before the milestone happened.

**Workflow:**

1. An invoice arrives; Odin records it rather than immediately alleging a breach.
2. Payment card shows `Invoice received ✓ / signed acceptance ? / dispute status ?`.
3. Supplier asks for payment. The draft response asks for the missing acceptance evidence, citing the payment clause.
4. An authorized reviewer attaches/links the acceptance record with its actual signing and receipt times.
5. The ledger derives the due date from the satisfied prerequisites and starts the appropriate clock.
6. A partial payment reduces principal rather than marking the whole invoice paid.

**Why useful:** it prevents the system from giving confidently premature payment or breach advice. It also protects commercial relationships by avoiding false escalation.

**Backend delta:** typed obligations with `all_of`/`any_of` prerequisites; proof records and provenance; state transitions `pending_evidence → scheduled → due → partially_satisfied → satisfied`, including disputed states. Keep payment allocation by invoice/reference and currency.

**Frontend delta:** a short evidence checklist attached to the payment/action, with “Request missing proof.” No need for a separate large module.

**Guardrail:** absence from Odin is not proof the acceptance never occurred. Phrase it as “not established from the records we have.” Never automatically withhold an actual payment through a bank integration.

### 4. Ask one useful question — “The answer changes depending on this one fact.”

**Simple meaning:** instead of generic low-confidence warnings, identify the missing fact that changes the recommended decision and ask only for that fact.

**Example:** whether a 45-minute outage was approved maintenance with sufficient notice changes supplier credit eligibility, while the customer credit rule remains different.

**Workflow:**

1. Event arrives with incomplete maintenance status.
2. Odin shows “One fact changes whether the supplier owes a credit: was this approved maintenance notified at least 48 hours earlier?”
3. Display two branches: if yes, supplier exclusion may apply; if no, test duration and other requirements. For 45 minutes the supplier threshold still fails either way, so this is **not** a useful question for supplier eligibility at that duration. Use a **180-minute** incident to demonstrate a question that genuinely changes the outcome.
4. Reviewer links the notification and approval evidence, or chooses unknown.
5. Only affected calculations/findings refresh. Unknown stays conditional; the system does not guess to finish.

This example intentionally checks that the requested information matters. For a 45-minute incident, a better question may be whether it was customer-visible or whether a customer claim was made.

**Why impressive:** the system demonstrates judgment about what it does not know. It turns clarification loops into a user-visible reduction in uncertainty.

**Backend delta:** evaluate scenario branches with a small set of typed predicates, rank questions by whether they change action/amount/deadline, and store the answer as evidence. No need for a sophisticated information-theory optimizer in two days.

**Frontend delta:** one question card with “why we need this,” branch consequences and evidence attachment/link. Prefer a question that changes the decision over a generic “provide more information.”

**Guardrail:** do not present a numerical confidence improvement or monetary value of information without a calibrated model. A human answer alone may need supporting proof.

### 5. Decision receipt — “Click any recommendation and see its proof.”

**Simple meaning:** a compact, reproducible record of the recommendation, not pages of agent chatter.

**Workflow:**

1. Open a proposed Nimbus claim or Willow service credit action.
2. See the question, source version/clauses, relevant event time, calculation and prerequisites.
3. Read three short statements: Loki's challenge, Heimdall's counterevidence and Tyr's decision. If there was no dispute, say so instead of inventing a debate.
4. Open the exact PDF highlight or the underlying calculation.
5. See actual evaluation coverage and security decisions. “Quote verified; semantic check not run” is a valid honest status.
6. Reviewer approves a specific draft revision. Later changes mark the receipt/action stale and invalidate approval.

**Why valuable:** a judge can challenge the product and immediately inspect its evidence. It makes the multi-agent system accountable rather than theatrical.

**Backend delta:** mostly joining existing workflow, artifact, report, eval and security IDs into an immutable snapshot; exact payload-bound approval and source hashes need the handoff fixes.

**Frontend delta:** one drawer/card shared across actions, alerts and reports. Top line: decision and why now. Then facts, calculation, uncertainty, debate, approval and technical trace link. Do not expose hidden chain-of-thought; use stored conclusions and concise reasons.

**Guardrail:** call it an evidence/decision receipt, not a legal certificate or guaranteed proof of truth. Source authenticity and correct interpretation are separate.

### 6. Smallest repair — “Change the least to make the whole portfolio consistent.”

**Simple meaning:** finding five risks is less helpful than identifying two coordinated changes that remove the underlying conflict.

**Examples:** UNIT-A lease extension versus customer relocation consent; Forge's delivery by May 20 versus SwiftRoute pickup May 21/delivery May 23.

**Workflow:**

1. Click “Compare repairs” on a dependency conflict.
2. For freight, compare earlier transport, a seller delivery amendment, or customer agreement if another downstream commitment is implicated.
3. Each option shows what it fixes, affected counterparties, required signatures, remaining unknown costs and unresolved obligations.
4. Choose an option for a draft proposal. The live contract stays unchanged until the relevant agreement is actually executed and uploaded.

**Backend delta:** for the demo, enumerate two or three explicitly defined candidate changes and re-evaluate affected predicates. A general contract optimizer is a later project. If alternative carriage cost is unknown, show unknown; do not invent a cheaper option.

**Frontend delta:** side-by-side repair cards with before/after dates and unresolved constraints. Reuse existing amendment diff and what-if views.

**Guardrail:** a local edit to a PDF or generated amendment does not bind another party. Existing conflict alerts/what-if screens alone are not this feature.

### 7. Claim rescue — “You earned a credit, but it expires unless you claim.”

**Simple meaning:** detect eligible recovery and assemble what is needed to preserve it within the contractual claim window.

**Example:** Nimbus incident credit requires a claim within 15 calendar days of incident end; Willow's customer credit has a separate ten-day claim requirement. An eligible incident is not the same as an accepted credit or cash receipt.

**Workflow:** qualifying incident → verify duration/exclusions → identify claimant and claim window → request monitoring logs/ticket → prepare correct recipient and clause-backed claim → human approves → record dispatch/delivery evidence if subsequently authorized → track credited invoice.

**UI:** conditional amount, time left, missing proof and named owner. A “Rescue ₹20,000” headline must say **potential credit subject to claim and eligibility** until established.

**Build limit:** automate packet assembly and reminders, not actual legal dispatch in the demo. Claim eligibility, filing, approval and application to an invoice are separate statuses.

### 8. Two clocks — “What happened is different from what we knew.”

**Simple meaning:** reconstruct both business reality and the information available to the system at a historical moment.

**Real V3 case:** EVT-V3-0013 includes a bank clearing event on January 8, received January 13. The corpus explicitly requires preserving the actual clearing time while evaluating at receipt time.

**Workflow:**

1. View January 10 “as known then”: a payment may be unconfirmed in the system.
2. Receive the January 13 bank confirmation describing January 8 clearing.
3. Today's corrected ledger reflects the actual payment date; historical receipt-aware view explains why a previous alert existed.
4. Show which alerts/drafts need withdrawal or correction, preserving the original decision history.

**Why strong:** it prevents future information leaking into past scenarios and handles late operational data sensibly. This is harder and more distinctive than a date slider that reads today's entire ledger.

**Build limit:** storing two timestamps and replaying one bounded case is feasible; full bitemporal persistence across every table is larger. Be explicit about scope.

### 9. Show what breaks the answer — “Try 30 minutes, then 31.”

**Simple meaning:** demonstrate that the rule engine handles boundary conditions and that changes have reasons.

**Workflow:** select the outage scenario → run 30, 31, 120 and 121 minutes → see customer/supplier eligibility switch at the respective strict thresholds → toggle approved maintenance → see the supplier exclusion applied while customer promise remains. Add one duplicate event and show no duplicate credit.

This is a **property-based or metamorphic check**: changing one input in a controlled way should produce a predictable change. Other strong properties: more qualifying overdue days do not lower uncapped simple interest; interest never exceeds its cap; partial payment never increases remaining principal; moving the evidence cutoff backward never reveals future events.

**Why judges may respond well:** it is evidence the system was engineered to be challenged, rather than a rehearsed answer for one PDF.

**Build limit:** deterministic assertions and a small comparison component; do not spend precious time asking multiple LLMs to recalculate identical math. Mark comparisons as executed tests only after running them.

### 10. No double counting — “These numbers are not the same kind of money.”

**Simple meaning:** separate ordinary fees, overdue principal, accrued interest, contingent damages and potential recoveries.

**Workflow:** click one incident's amount → see customer credit obligation, supplier credit receivable, conditions, caps and timing separately → reveal other liabilities that are alternatives or offsets rather than additive → compare gross obligation with eligible recovery and residual uncertainty.

Use a money waterfall or ledger with typed rows. A supplier credit cap is not a positive company liability; an ordinary annual fee is not a damages estimate; a liability cap is not automatically incurred loss. Do not display a risk-weighted “expected loss” without a defensible probability model.

**Why useful:** improves the credibility of every other USP. A correct plain ledger can be more impressive than a large exposure gauge that cannot explain its total.

## Additional ideas worth retaining for later

**11 — Safe action rehearsal.** Select a termination draft, simulate only the supported consequences under its current proposal, and show export/continuity duties and unresolved consent. Present it as a scenario, never an executed change. Reuses existing what-if and redlines but adds a clear action-to-outcome connection.

**12 — Security decision replay.** In a disposable workspace, submit a synthetic email telling an agent to send confidential data. Show its detector decision, quarantine state, blocked/unavailable tool capability, redacted logs and **zero actual external sends**. Pair with a benign legal phrase to show false-positive handling. Detecting a familiar phrase alone is not proof of robust security. See [OWASP's prompt-injection discussion](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) for why layered boundaries matter.

**13 — Consent dependency.** A relocation draft or signed vendor amendment does not automatically change Willow's service-location promise. Display “waiting for the correct party's written consent” and keep the old obligation active. This is a useful guard against the false impression that “apply amendment” resolves every linked contract.

**14 — Cost of waiting.** Compare “prepare claim while the window is open” with “after the contractual claim deadline.” State the amount whose eligibility is at risk and the assumptions. Do not invent daily business loss where no contractual or user-supplied amount exists.

**15 — One fix, several protected promises.** Highlight shared infrastructure or data dependencies across hosting, backup and the customer portal. Ask which obligations would be affected by a single underlying incident; avoid counting several alerts as several independent losses. Start with the observed graph and sourced IDs, not unsupported causal certainty.

**16 — Explainable change reuse.** Upload a revised clause and show the impacted facts/findings/obligations, what was recomputed and which unaffected results were reused. Prove the saved calls/tokens using actual counters. The pulled branch already has report diffs; a new USP requires meaningful dependency-aware invalidation, not a second diff display.

**17 — Missing document radar.** “This order references acceptance/consent evidence that is not in this workspace.” Show why it matters, the affected decision and how to supply proof. Do not say the document does not exist outside Odin.

**18 — Notice validity check.** Before approval, check source notice address, authorized recipient, channel, timezone, exact deadline, required information and delivery evidence. A valid Gmail address alone is insufficient. Display unknown contractual requirements honestly and require human confirmation.

**19 — Portable dispute packet.** Export the incident chronology, source pages, version hashes, calculations, disagreement, decision and draft. Fix PDF hyperlinks and authorization first. Avoid implying an internal hash makes evidence court-admissible or independently authentic.

**20 — Risk-based attention queue.** Put “claim closes tomorrow” above “generic low-confidence ambiguity next year,” with a plain reason. Rank by contractual urgency, consequence band and evidence state; give users control. Do not multiply uncalibrated confidence by money and call it expected value.

**21 — Stress lab.** Generalize boundary testing into a small scenario matrix, e.g. outage duration × maintenance approval × claim time. Explain rule transitions and unsupported regions. Keep experiments isolated and make simulated state visibly different from current state.

**22 — Negotiation pack.** For the maintenance mismatch, generate a targeted proposal to align an exclusion or threshold, explain the intended effect and show remaining gaps. A counterparty must still agree. Reuse the current amendment proposal UI; clause language should be reviewed by a human rather than sold as optimized legal advice.

## Features I would not spend the next two days building

- Another chat persona, voice assistant or generic contract summarizer: low differentiation against the PS and existing product.
- More agents just to increase the count: weak if responsibilities and evidence do not improve.
- A new regulatory-news crawler: accuracy, source authority, applicability and timeliness are a substantial separate project.
- Blockchain/notarization for every PDF: hashing alone does not establish document authenticity or correct interpretation.
- Autonomous sending, auto-paying or silently accepting amendments: unnecessary demo risk and contrary to the PS's human-approval requirement.
- A broad legal-outcome probability/ROI predictor: data is insufficient for calibrated claims.
- A fabricated 99% trust score or an OWASP badge from a few fixture tests.
- Full enterprise connectors or a new queue platform before the existing invocation/evidence lifecycle is honest.

## Concrete 48-hour feature selection

### Recommended package: protection gap + decision receipt

Spend available feature time on **#1 and #5**, reusing the existing workflow and graph. Add a small **#9 boundary comparison** if calculations are correct. This is the strongest compact story for this particular corpus.

**Why this package:** it shows multi-agent coordination, cross-contract reasoning, real event impact, exact source evidence, deterministic calculation and safe action. It upgrades capabilities already present, which reduces build risk.

### Alternative package: proof before payment + one useful question

Choose **#3 and #4** if event/financial prerequisites can be implemented more reliably than downstream SLA mapping. This is less visually dramatic but highly useful, testable and credible. Add the same shared decision receipt if time permits.

### Stretch after either package works

Add one **#2 last-safe-moment** chain for UNIT-A. Do not attempt the general repair planner, temporal replay and negotiation optimizer at the same time. If only one day remains, a correct two-clause gap with a working source/decision drawer is enough scope.

## A three-minute judged demonstration

| Time | Show | What it demonstrates |
|---|---|---|
| 0:00–0:20 | Aurora's business context and nine uploaded contracts; one focused dependency | The system understands a portfolio and business promises |
| 0:20–0:55 | Hosting vs portal threshold/exclusion comparison, both source highlights | Hidden cross-contract protection gap |
| 0:55–1:25 | A 45-minute approved-maintenance scenario; customer claim conditions visible | Supplier compliance can still leave customer exposure |
| 1:25–1:55 | Relevant Loki challenge, Heimdall evidence, Tyr decision in the receipt | Agents test a finding and retain uncertainty |
| 1:55–2:20 | Proposed remedy or claim packet with prerequisite/owner/deadline | Concrete action, not another summary |
| 2:20–2:45 | Change a threshold input; show a real passed/failed boundary assertion and trace | Reproducible engineering and honest evaluation |
| 2:45–3:00 | Human approval state; optional synthetic quarantine result | Human control and actual safety boundary |

Use the scenario view with a visible “Simulation” label. Do not replay independent corpus alternatives into one live ledger. Do not rely on real Gmail arrival timing or send a real notice during judging. If a displayed step is precomputed, label its source and actual execution time; avoid presenting prerecorded output as a fresh live run.

## How to know the USP is real

For each selected feature, a judge should be able to change a relevant input and receive a correctly changed, cited result. Every monetary number should have a traceable formula and conditions. Every state change should have a known source, clock and owner. An unknown fact should remain unknown, and a proposal should remain a proposal until the right evidence arrives.

The most persuasive claim is specific: **“Our system can show why a supplier-compliant maintenance event can still create a customer credit obligation, identify the missing evidence, and prepare a reviewable response.”** It is stronger than claiming to solve all contractual risk.

## Evidence and attribution

Source examples come from authored fixture PDFs, particularly AUR-2027-001 §§2.1, 3.1, 4.1; AUR-2027-002 §§3.1, 4.1, 5.1; the Forge device/integration agreements, UNIT-A lease, SwiftRoute freight agreement, V3 context and event goldens. These are test materials, not independently reviewed legal advice or verified commercial facts.

Local references: [V3 portfolio guide](C:/Users/offic/OneDrive/Desktop/Ragnarok/ODIN_7_Companies_9_Contracts/corpus_v3/README.md), [previous observed website failures](C:/Users/offic/OneDrive/Desktop/Ragnarok/reports/website-audit-20261026/REPORT.md), [current implementation handoff](C:/Users/offic/OneDrive/Desktop/Ragnarok/docs/handoffs/2026-10-26-EVAL-SECURITY-CLAUDE-HANDOFF.md). Current-code investigation distinguished existing what-if/graph/debate/report/security/eval features from the proposed extensions. Public product pages cited above support the limited comparison only; none establishes that these combinations are globally unique.
