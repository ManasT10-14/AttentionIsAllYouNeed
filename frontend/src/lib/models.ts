import { z } from 'zod';

export const contractSchema = z.object({
  id: z.string(), name: z.string(), party: z.string(), category: z.string(), owner: z.string(),
  renewal: z.string().date(), value: z.number().nonnegative(), confidence: z.number().min(0).max(1)
});
export const obligationSchema = z.object({
  id: z.string(), contractId: z.string(), title: z.string(), type: z.enum(['Renewal', 'Payment', 'Compliance', 'Service level']),
  deadline: z.string().date(), amount: z.number().nonnegative(), dailyPenalty: z.number().nonnegative(),
  clause: z.string(), quote: z.string(), confidence: z.number().min(0).max(1)
});
export const findingSchema = z.object({
  id: z.string(), obligationId: z.string(), agent: z.enum(['Loki', 'Heimdall', 'Tyr', 'Thor']),
  kind: z.enum(['Attack', 'Verification', 'Ruling', 'Extraction']), title: z.string(), body: z.string(),
  confidence: z.number().min(0).max(1), timestamp: z.string()
});
export const actionSchema = z.object({
  id: z.string(), obligationId: z.string(), title: z.string(), draft: z.string(),
  status: z.enum(['Needs review', 'Approved', 'Dismissed']), recipient: z.string()
});
export const eventSchema = z.object({
  id: z.string(), contractId: z.string(), title: z.string(), body: z.string(), date: z.string().date(),
  severity: z.enum(['High', 'Medium', 'Low'])
});
export const portfolioSchema = z.object({
  workspace: z.string(), asOf: z.string().date(), contracts: z.array(contractSchema),
  obligations: z.array(obligationSchema), findings: z.array(findingSchema), actions: z.array(actionSchema), events: z.array(eventSchema),
  relationships: z.array(z.object({ id: z.string(), sourceObligationId: z.string(), targetObligationId: z.string(), kind: z.enum(['dependency', 'conflict']), label: z.string(), rationale: z.string(), confidence: z.number().min(0).max(1) })).default([])
}).superRefine((data, context) => {
  const contracts = new Set(data.contracts.map(item => item.id));
  const obligations = new Set(data.obligations.map(item => item.id));
  if (contracts.size !== data.contracts.length || obligations.size !== data.obligations.length) {
    context.addIssue({ code: 'custom', message: 'Contract and obligation identifiers must be unique.' });
  }
  if (data.obligations.some(item => !contracts.has(item.contractId)) || data.events.some(item => !contracts.has(item.contractId))) {
    context.addIssue({ code: 'custom', message: 'All contract references must resolve.' });
  }
  if ([...data.actions, ...data.findings].some(item => !obligations.has(item.obligationId))) {
    context.addIssue({ code: 'custom', message: 'All obligation references must resolve.' });
  }
  if (data.relationships.some(item => !obligations.has(item.sourceObligationId) || !obligations.has(item.targetObligationId))) context.addIssue({ code: 'custom', message: 'All relationship references must resolve.' });
});

export type Portfolio = z.infer<typeof portfolioSchema>;
export type Contract = z.infer<typeof contractSchema>;
export type Obligation = z.infer<typeof obligationSchema>;
export type Finding = z.infer<typeof findingSchema>;
export type Action = z.infer<typeof actionSchema>;
