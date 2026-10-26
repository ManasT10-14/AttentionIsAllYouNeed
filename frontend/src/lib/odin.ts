import { list, number, record, text, type ApiRecord } from './api';

/** Pack-aware helpers: citation refs, document families, simulation and bundle-import shapes. Tolerant of key variants until backend samples settle. */

/** "A2 §3.2" / "B1 Section G". `ref` is the clause reference as written; falls back to the stored number. */
export function citationLabel(c: ApiRecord): string {
  const doc = text(c.contract_id, '');
  const ref = text(c.ref, '') || (/^\d/.test(text(c.clause_number, '')) ? '§' + text(c.clause_number) : /^[A-Z]$/.test(text(c.clause_number, '')) ? 'Section ' + text(c.clause_number) : text(c.clause_number, ''));
  return [doc, ref].filter(Boolean).join(' ');
}

export type Relation = { from: string; to: string; kind: string; detail: string };
const RELATION_VERB: Record<string, string> = { incorporates: 'incorporates', amends: 'amends', addendum_to: 'addendum to' };
export function relationsOf(source: unknown): Relation[] {
  const o = record(source);
  const rows = list(o.relations ?? o.doc_relations ?? record(o.meta).relations);
  return rows.map(r => ({ from: text(r.from_doc ?? r.from, ''), to: text(r.to_doc ?? r.to, ''), kind: text(r.relation ?? r.kind, ''), detail: text(r.detail, '') })).filter(r => r.from && r.to);
}
/** Badges for one document: "Incorporated by A1, B1, C1", "Amends A2", "Addendum to B1". */
export function familyBadges(docId: string, relations: Relation[]): string[] {
  const by = (pred: (r: Relation) => boolean, pick: (r: Relation) => string) => relations.filter(pred).map(pick);
  const out: string[] = [];
  const incorporatedBy = by(r => r.kind === 'incorporates' && r.to === docId, r => r.from);
  const incorporates = by(r => r.kind === 'incorporates' && r.from === docId, r => r.to);
  const amends = by(r => r.kind === 'amends' && r.from === docId, r => r.to);
  const amendedBy = by(r => r.kind === 'amends' && r.to === docId, r => r.from);
  const addendum = by(r => r.kind === 'addendum_to' && r.from === docId, r => r.to);
  const addenda = by(r => r.kind === 'addendum_to' && r.to === docId, r => r.from);
  if (incorporatedBy.length) out.push('Incorporated by ' + incorporatedBy.join(', '));
  if (incorporates.length) out.push('Incorporates ' + incorporates.join(', '));
  if (amends.length) out.push('Amends ' + amends.join(', '));
  if (amendedBy.length) out.push('Amended by ' + amendedBy.join(', '));
  if (addendum.length) out.push('Addendum to ' + addendum.join(', '));
  if (addenda.length) out.push('Addendum: ' + addenda.join(', '));
  return out;
}
export function relationVerb(kind: string) { return RELATION_VERB[kind] ?? kind.replaceAll('_', ' '); }

export type Override = { by_doc: string; by_ref: string; effective: string; original: string; effectiveText: string };
/** Amendment info on a clause (or a clause_override record): "as amended by A3 Section 1 effective 2027-01-01". */
export function overrideOf(clause: unknown): Override | null {
  const c = record(clause); const o = record(c.override ?? c.amended_by ?? c.amendment);
  const by = text(o.by_doc ?? c.by_doc, '');
  if (!by) return null;
  return { by_doc: by, by_ref: text(o.by_ref ?? c.by_ref, ''), effective: text(o.effective ?? o.effective_date ?? c.effective, ''), original: text(c.original_text ?? o.original_text ?? c.text, ''), effectiveText: text(o.new_text ?? c.effective_text ?? c.new_text, '') };
}

export const CHANNEL_LABEL: Record<string, string> = { email: 'Email', system: 'System', status_log: 'Status log', phone: 'Phone' };
export type SimEvent = { id: string; external_id: string; channel: string; sender: string; recipient: string; source: string; subject: string; status: string; reason: string; line: number | undefined; timestamp: string };
export function simEvent(e: unknown): SimEvent {
  const r = record(e);
  return { id: text(r.id ?? r.event_id, ''), external_id: text(r.external_id, ''), channel: text(r.channel, ''), sender: text(r.sender ?? r.from, ''), recipient: text(r.recipient ?? r.to, ''), source: text(r.source, ''), subject: text(r.subject ?? r.title, ''), status: text(r.status, ''), reason: text(r.reject_reason ?? r.reason, ''), line: number(r.line ?? r.line_number ?? record(r.meta).line), timestamp: text(r.timestamp ?? r.occurred_at ?? r.date, '') };
}
/** Event feed in timestamp order; rejected malformed lines (no timestamp) sort last. */
export function eventFeed(events: unknown): SimEvent[] {
  return list(events).map(simEvent).sort((a, b) => (a.timestamp || '￿').localeCompare(b.timestamp || '￿'));
}

export type Checkpoint = { date: string; label: string; reached: boolean; snapshot: ApiRecord };
/** Normalises GET /api/simulation (clock + checkpoints) into ordered checkpoint records. */
export function checkpointsOf(sim: unknown, now: string): Checkpoint[] {
  const o = record(sim); const raw = Array.isArray(o.checkpoints) ? o.checkpoints : [];
  return raw.map((c, i) => {
    const r = record(c); const date = typeof c === 'string' ? c : text(r.checkpoint ?? r.date, '');
    return { date, label: 'Checkpoint ' + (i + 1), reached: Boolean(date) && date <= now, snapshot: r };
  }).filter(c => c.date);
}
/** Position (0..100) of a date on the start..last-checkpoint track. */
export function trackPosition(date: string, start: string, end: string): number {
  const a = Date.parse(start), b = Date.parse(end), d = Date.parse(date);
  if (!(b > a) || Number.isNaN(d)) return 0;
  return Math.max(0, Math.min(100, ((d - a) / (b - a)) * 100));
}
/** Snapshot metric rows for compare view: [label, a, b, changed]. */
export function compareSnapshots(a: ApiRecord, b: ApiRecord): { key: string; a: number; b: number; delta: number }[] {
  const count = (v: unknown) => Array.isArray(v) ? v.length : number(v) ?? number(record(v).expected) ?? number(record(v).amount) ?? 0;
  return ['obligations', 'deadlines', 'exposure', 'open_risks', 'alerts', 'actions'].map(key => ({ key, a: count(a[key]), b: count(b[key]), delta: count(b[key]) - count(a[key]) }));
}

/** Bundle import summary counts, accepting either a nested `counts` object or flat fields. */
export function bundleSummary(result: unknown): { label: string; value: number }[] {
  const r = record(result); const c = { ...r, ...record(r.counts), ...record(r.summary) };
  const n = (...keys: string[]) => { for (const k of keys) { const v = c[k]; if (Array.isArray(v)) return v.length; const x = number(v); if (x !== undefined) return x; } return 0; };
  return [
    { label: 'Documents', value: n('documents', 'docs', 'contracts') }, { label: 'Clauses', value: n('clauses') }, { label: 'Relations', value: n('relations', 'doc_relations') },
    { label: 'Ledger rows', value: n('ledger', 'ledger_rows') }, { label: 'Holidays', value: n('holidays') }, { label: 'Warnings', value: n('warnings') },
  ];
}
export function bundleWarnings(result: unknown): string[] { const w = record(result).warnings; return Array.isArray(w) ? w.map(x => text(typeof x === 'string' ? x : record(x).message ?? JSON.stringify(x))) : []; }

export const ASK_STARTERS = [
  'What SLA credit can Quillhub claim from StratoNode for March 2027?',
  'Does A3 change how credit requests work?',
  'Which contracts conflict on exclusivity?',
  "Is Quillhub's insurance compliant with B1?",
  'Which deadlines fall before the next checkpoint?',
];
