import { list, record, text, type ApiRecord } from './api';
export function reportReadiness(report: ApiRecord): 'analysis_missing' | 'summary_missing' | 'ready' {
 const summary = record(report.summary);
 if (report.kind === 'contract' && !report.key_terms && !list(report.risks).length && !list(report.actions).length && !list(report.timeline).length) return 'analysis_missing';
 if (summary.unavailable || report.summary_status === 'unavailable' || !text(summary.executive_summary, '').trim() || text(summary.executive_summary, '').startsWith('(summary unavailable:')) return 'summary_missing';
 return 'ready';
}
