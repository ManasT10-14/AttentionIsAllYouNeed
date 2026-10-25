import { list, number, record, text, type ApiRecord } from './api';

export const QUALITY_METRICS = ['citation_faithfulness', 'extraction_completeness', 'groundedness'];
export function hasScore(metric: ApiRecord) {
 return number(metric.score) !== undefined && ['passed', 'failed'].includes(text(metric.status, ''));
}
export function qualityCoverage(run: ApiRecord) {
 const metrics = list(run.metrics).filter(m => QUALITY_METRICS.includes(text(m.name, '')));
 const scored = metrics.filter(hasScore).length;
 return { scored, total: metrics.length, label: scored ? `${scored}/${metrics.length} quality checks scored` : 'Quality not assessed' };
}
export function metricHistory(runs: ApiRecord[], name: string) {
 const attempts: ApiRecord[] = runs.flatMap(r => list(r.metrics).filter(m => text(m.name, '').split(':')[0] === name).map<ApiRecord>(m => ({ ...m, run_id: r.run_id })));
 return { attempts, scored: attempts.filter(hasScore), skipped: attempts.filter(m => m.status === 'skipped'), errors: attempts.filter(m => m.status === 'error' || m.status === 'invalid') };
}
export function reviewFindings(current: ApiRecord, workflow: ApiRecord, runId: string, contract = ''): ApiRecord[] {
 const findings: ApiRecord[] = runId ? list(workflow.debate).map<ApiRecord>(d => ({ ...record(d.finding), verifications: d.verifications, ruling: d.ruling })) : list(current.findings);
 return findings.filter(f => !contract || f.contract_id === contract).map(f => ({
  ...f,
  verifications: f.verifications ?? list(current.verifications).filter(v => v.finding_id === f.id),
  ruling: f.ruling ?? list(current.rulings).find(r => r.finding_id === f.id),
 }));
}
export function filterReviewMessages(messages: ApiRecord[], filters: { agent: string; kind: string; search: string; newest: boolean }) {
 const rows = messages.filter(m => (!filters.agent || text(m.sender, '').toLowerCase() === filters.agent.toLowerCase())
  && (!filters.kind || m.kind === filters.kind)
  && (!filters.search || [m.summary, m.sender, m.receiver, m.contract_id, m.run_id].map(v => text(v, '')).join(' ').toLowerCase().includes(filters.search.toLowerCase())));
 return [...rows].sort((a, b) => {
  const order = text(a.ts, '').localeCompare(text(b.ts, ''));
  return filters.newest ? -order : order;
 });
}
export function missingReportExplanation(run: ApiRecord) {
 if (run.status === 'running' || run.status === 'pending') return 'This run is still in progress. A saved report will appear here if the run produces one.';
 if (run.kind === 'event') return 'Event reviews use an event report rather than a company-report snapshot. No linked event report is available for this run.';
 if (run.kind === 'whatif') return 'What-if results belong to the scenario; these runs do not save a company-report snapshot.';
 if (run.kind === 'ask') return 'Question runs produce an answer and citations rather than a company-report snapshot.';
 return 'No company-report snapshot was saved for this run. Review the run errors and messages below; the available execution records are shown here.';
}
