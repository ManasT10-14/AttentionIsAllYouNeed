import { portfolioSchema } from './models';

export const demoPortfolio = portfolioSchema.parse({
  workspace: 'Northstar Labs', asOf: '2026-10-25',
  relationships: [{ id: 'sample-conflict', sourceObligationId: 'renewal', targetObligationId: 'payment', kind: 'conflict', label: 'Sample review conflict', rationale: 'Illustrative operational conflict: prioritizing the payment cure could delay review of the earlier renewal notice. This is a review hypothesis, not a verified contradiction between these clauses.', confidence: .62 }],
  contracts: [
    { id: 'cobalt', name: 'Cobalt Systems MSA', party: 'Cobalt Systems', category: 'Master service agreement', owner: 'Legal operations', renewal: '2027-01-18', value: 120000, confidence: .96 },
    { id: 'orbital', name: 'Orbital Cloud Services', party: 'Orbital Cloud', category: 'Cloud infrastructure', owner: 'IT operations', renewal: '2027-01-03', value: 74000, confidence: .93 },
    { id: 'tanner', name: 'Tanner & Cole Lease', party: 'Tanner & Cole', category: 'Commercial lease', owner: 'Finance', renewal: '2027-03-31', value: 96000, confidence: .89 },
    { id: 'monarch', name: 'Monarch Design Partner', party: 'Monarch Inc.', category: 'Statement of work', owner: 'Procurement', renewal: '2027-06-14', value: 42000, confidence: .94 }
  ],
  obligations: [
    { id: 'renewal', contractId: 'cobalt', title: 'Send renewal notice', type: 'Renewal', deadline: '2026-11-19', amount: 24000, dailyPenalty: 0, clause: '12.2', quote: 'This Agreement shall renew for a further twelve months unless either party provides written notice at least sixty days before the renewal date.', confidence: .96 },
    { id: 'payment', contractId: 'orbital', title: 'Resolve overdue invoice', type: 'Payment', deadline: '2026-12-01', amount: 18500, dailyPenalty: 250, clause: '8.4', quote: 'Unpaid balances outstanding after the cure period are subject to a fixed charge of $18,500 and an additional $250 for each day thereafter.', confidence: .93 },
    { id: 'insurance', contractId: 'tanner', title: 'Update insurance certificate', type: 'Compliance', deadline: '2026-11-13', amount: 9200, dailyPenalty: 0, clause: '12.1', quote: 'The tenant must provide a current certificate of insurance by November 13, 2026. Failure to cure by this date incurs a one-time charge of $9,200.', confidence: .89 },
    { id: 'privacy', contractId: 'monarch', title: 'Renew data processing addendum', type: 'Compliance', deadline: '2026-12-15', amount: 12500, dailyPenalty: 0, clause: '6.3', quote: 'The data processing addendum must be renewed no later than December 15, 2026. A lapse triggers the agreed remediation charge of $12,500.', confidence: .94 }
  ],
  findings: [
    { id: 'f1', obligationId: 'renewal', agent: 'Loki', kind: 'Attack', title: 'A notice window can become an involuntary renewal', body: 'Clause 12.2 makes renewal automatic. An internal decision to terminate is insufficient: the notice must be delivered before the deadline.', confidence: .94, timestamp: '2026-10-25T09:12:00Z' },
    { id: 'f2', obligationId: 'renewal', agent: 'Heimdall', kind: 'Verification', title: 'Delivery evidence has not been recorded', body: 'The sample notice register contains no delivery receipt. The notice deadline is verified against the extracted renewal term.', confidence: .96, timestamp: '2026-10-25T09:14:00Z' },
    { id: 'f3', obligationId: 'renewal', agent: 'Tyr', kind: 'Ruling', title: 'Prepare the notice for human approval', body: 'The source supports the finding. Prepare a written notice, confirm the intended commercial outcome with the owner, and obtain approval before delivery.', confidence: .95, timestamp: '2026-10-25T09:17:00Z' },
    { id: 'f4', obligationId: 'payment', agent: 'Thor', kind: 'Extraction', title: 'Daily penalty extracted', body: 'The fixed charge and daily accrual are separately recorded. The daily charge only begins after the cure deadline.', confidence: .93, timestamp: '2026-10-25T09:20:00Z' }
  ],
  actions: [
    { id: 'a1', obligationId: 'renewal', title: 'Review renewal notice', status: 'Needs review', recipient: 'Cobalt Systems · legal contact', draft: 'Subject: Notice of non-renewal — Master Service Agreement\n\nDear Cobalt Systems team,\n\nPursuant to clause 12.2 of the Master Service Agreement, Northstar Labs provides notice of its intention not to renew the Agreement at the end of the current term.\n\nPlease acknowledge receipt and confirm the transition obligations that apply. This draft is subject to confirmation of the commercial decision and delivery requirements.\n\nNorthstar Labs\nLegal Operations' },
    { id: 'a2', obligationId: 'payment', title: 'Review payment escalation', status: 'Needs review', recipient: 'Northstar Labs · finance owner', draft: 'Subject: Action required — Orbital invoice cure period\n\nPlease reconcile the outstanding Orbital balance before December 1, 2026. Clause 8.4 provides for a fixed charge of $18,500 plus $250 per day after the cure deadline.\n\nConfirm the invoice amount, any dispute, and the payment authorization with Finance before taking action.\n\nLegal Operations' },
    { id: 'a3', obligationId: 'insurance', title: 'Request current insurance', status: 'Needs review', recipient: 'Northstar Labs · facilities owner', draft: 'Subject: Current insurance certificate required\n\nPlease provide the current certificate of insurance required by clause 12.1 of the Tanner & Cole lease before November 13, 2026.\n\nPlease verify the coverage dates and forward the certificate for review.\n\nLegal Operations' }
  ],
  events: [
    { id: 'e1', contractId: 'orbital', title: 'Payment discrepancy recorded', body: 'Finance has not confirmed settlement of the outstanding balance. The contractual cure period remains open.', date: '2026-10-25', severity: 'High' },
    { id: 'e2', contractId: 'cobalt', title: 'Renewal review requested', body: 'The business owner requested a review of renewal options and notice delivery requirements.', date: '2026-10-24', severity: 'Medium' },
    { id: 'e3', contractId: 'tanner', title: 'Certificate update requested', body: 'Facilities has been asked to provide updated insurance documentation before the compliance deadline.', date: '2026-10-23', severity: 'Medium' }
  ]
});
