import { list, record, text, type ApiRecord } from './api';

const labels: Record<string, string> = {
  analysis: 'Contract analysis', event: 'Event review', update: 'Contract update',
  report: 'Report refresh', whatif: 'What-if scenario', ask: 'Contract question',
};

/** Derive useful labels from recorded scope, without inventing outcomes. */
export function runTitle(run: ApiRecord, contracts: ApiRecord[] = [], events: ApiRecord[] = []) {
  const explicit = text(run.title, '').trim();
  if (explicit) return explicit;
  const kind = text(run.kind ?? run.run_kind, '');
  const label = labels[kind] ?? (kind ? kind.replaceAll('_', ' ') : 'Agent run');
  const links = record(record(run.workplan).links);
  const eventId = text(run.event_id ?? links.event_id, '');
  const event = events.find(e => (e.id ?? e.event_id) === eventId);
  const subject = text(event?.subject || event?.event_type, '').replaceAll('_', ' ');
  if (eventId) return `${label} · ${subject || eventId}`;
  const scoped = text(run.contract_id ?? links.contract_id, '');
  const ids = scoped ? [scoped] : [...new Set(list(record(run.workplan).workstreams)
    .map(w => text(w.contract_id, '')).filter(id => id && id !== 'cross'))];
  if (ids.length === 1) {
    const contract = contracts.find(c => (c.contract_id ?? c.id) === ids[0]);
    return `${label} · ${text(contract?.title, ids[0])}`;
  }
  if (ids.length) return `${label} · ${ids.length} agreements`;
  if (typeof run.new_findings === 'number') return `${label} · ${run.new_findings} new findings`;
  return label;
}

/** Keep runs without snapshots visible, and preserve existing snapshot metadata. */
export function reportRuns(snapshots: ApiRecord[], runs: ApiRecord[]): ApiRecord[] {
  const merged = new Map<string, ApiRecord>(runs.map(r => [text(r.id), { ...r, run_id: r.id, has_snapshot: false }]));
  for (const s of snapshots) {
    const id = text(s.run_id);
    merged.set(id, { ...merged.get(id), ...s, has_snapshot: true });
  }
  return [...merged.values()].sort((a, b) =>
    text(b.started_at ?? b.generated_at, '').localeCompare(text(a.started_at ?? a.generated_at, '')));
}

export function runReportTarget(workflow: ApiRecord): { kind: 'run' | 'event'; id: string } | null {
  const reports = list(workflow.reports);
  const runId = text(record(workflow.run).id, '');
  if (runId && reports.some(r => r.kind === 'run')) return { kind: 'run', id: runId };
  if (reports.some(r => r.kind === 'event') && workflow.event_id) return { kind: 'event', id: text(workflow.event_id) };
  return null;
}
