import { list, record, text, type ApiRecord } from './api';

/** Stop at the captured end: replay never invents a workflow step. */
export function nextReplayIndex(index: number, count: number): number | null {
 return index >= 0 && index + 1 < count ? index + 1 : null;
}
export function relatedMessageFindings(message: ApiRecord, context: ApiRecord): { requested: string[]; found: ApiRecord[]; missing: string[] } {
 const payload = record(message.payload);
 const ids = [payload.finding_id, message.finding_id,
  ...(Array.isArray(payload.finding_ids) ? payload.finding_ids : []),
  ...(Array.isArray(payload.disputed) ? payload.disputed : []),
  ...(Array.isArray(payload.related_finding_ids) ? payload.related_finding_ids : []),
 ].filter((id): id is string => typeof id === 'string' && Boolean(id));
 const requested = [...new Set(ids)];
 const candidates = [...list(context.findings), ...list(record(context.outputs).finding), ...list(context.debate).map(d => record(d.finding))];
 const byId = new Map(candidates.map(f => [text(f.id, ''), f]));
 return { requested, found: requested.flatMap(id => byId.has(id) ? [byId.get(id)!] : []), missing: requested.filter(id => !byId.has(id)) };
}
export function enrichWorkflowSteps(steps: ApiRecord[], messages: ApiRecord[]): ApiRecord[] {
 const byId = new Map(messages.filter(m => m.id).map(m => [text(m.id), m]));
 return steps.map(step => {
  const message = byId.get(text(step.id));
  return message ? { ...message, ...step, payload: message.payload ?? step.payload } : step;
 });
}

/** Use already loaded evidence when an older server cannot enrich a message. */
export function availableMessageResult(message: ApiRecord, context: ApiRecord): ApiRecord {
 const payload = record(message.payload); const sections: ApiRecord[] = [];
 const add = (title: string, value: unknown) => { if (value && (!Array.isArray(value) || value.length)) sections.push({title, value}); };
 const findings = relatedMessageFindings(message, context).found;
 const ids = new Set(findings.map(f => text(f.id)));
 const debate = list(context.debate).filter(d => ids.has(text(record(d.finding).id)));
 const verifications = [...list(context.verifications), ...debate.flatMap(d => list(d.verifications))].filter(v => ids.has(text(v.finding_id)));
 const rulings = [...list(context.rulings), ...debate.map(d => record(d.ruling))].filter(r => ids.has(text(r.finding_id)));
 if (payload.result_snapshot) {
  const rep = record(payload.result_snapshot);
  add('Saved report summary', rep.summary); add('Leading risks', rep.leading_risks ?? rep.risks ?? rep.conflicts);
  add('Next actions', rep.prioritized_actions ?? rep.actions); add('Financial exposure', rep.total_exposure ?? rep.exposure);
  add('Clause references', rep.references);
 }
 add('Referenced findings and evidence', findings);
 add('Verification verdicts and rationale', payload.verification_results ?? verifications);
 add('Rulings and decisions', rulings);
 const actionIds = new Set(Array.isArray(payload.action_ids) ? payload.action_ids : []);
 add('Drafted actions', [...list(context.actions), ...list(record(context.outputs).action)].filter(a => actionIds.has(a.id)));
 if (message.sender === 'odin') add('Recorded work plan', context.workstreams);
 if (message.sender === 'norns') add('Recorded exposure and assumptions', payload.exposure);
 return {source: payload.result_snapshot ? 'message_time_snapshot' : 'available_records', sections,
  notice: 'Showing evidence already loaded for this review. Available records may have changed since the message.'};
}
