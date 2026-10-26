'use client';
import { useState } from 'react';
import { Download } from 'lucide-react';
import { useResource } from '@/lib/use-resource';
import { dateText, list, record, text, type ApiRecord } from '@/lib/api';
import { bundleSummary, bundleWarnings, familyBadges, overrideOf, relationsOf, type Relation } from '@/lib/odin';
import { useWorkspace } from './providers';
import { Badge, Button, Panel, PanelTitle } from './ui';
import { MutationFeedback, RecordTable, ResourceState, useMutation } from './api-ui';

export function ExternalId({ contract }: { contract: ApiRecord }) {
  const ext = text(contract.external_id ?? record(contract.meta).external_id, '');
  return ext && ext !== text(contract.id, '') ? <code className="external-id">{ext}</code> : null;
}
export function FamilyBadges({ docId, relations }: { docId: string; relations: Relation[] }) {
  const badges = familyBadges(docId, relations);
  return badges.length ? <span className="family-badges">{badges.map(b => <Badge key={b} tone="purple">{b}</Badge>)}</span> : null;
}
/** "Amended by A3 Section 1 (effective 1 Jan 2027)" with both the original and the effective text. */
export function AmendedBanner({ clause }: { clause: ApiRecord }) {
  const o = overrideOf(clause); if (!o) return null;
  return <div className="report-notice amended-banner" role="note"><strong>Amended by {o.by_doc} {o.by_ref}{o.effective ? ' (effective ' + dateText(o.effective) + ')' : ''}</strong>
    {o.effectiveText && <p><b>Effective text:</b> {o.effectiveText}</p>}{o.original && <details><summary>Original text</summary><p>{o.original}</p></details>}</div>;
}
export function relationsFromContracts(rows: ApiRecord[], extra: Relation[] = []): Relation[] {
  const seen = new Set<string>(); const out: Relation[] = [];
  for (const r of [...rows.flatMap(c => relationsOf(c)), ...extra]) { const k = r.from + r.kind + r.to; if (!seen.has(k)) { seen.add(k); out.push(r); } }
  return out;
}

/** Admin: import the official bundle, then show what landed. */
export function BundlePanel({ onImported }: { onImported: (relations: Relation[]) => void }) {
  const { canAdmin, demo } = useWorkspace(); const m = useMutation(); const [result, setResult] = useState<unknown>(null);
  async function run() { const r = await m.run('/api/bundle/import?analyze=true'); if (r !== undefined) { setResult(r); onImported(relationsOf(r)); } }
  const warnings = bundleWarnings(result);
  const [recheck, setRecheck] = useState<ApiRecord | null>(null);
  async function verifySaved() { const r = await m.run('/api/citations/recheck'); if (r !== undefined) setRecheck(record(r)); }
  return <Panel><PanelTitle title="Official bundle" description="Quillhub Inc. contracts, payments ledger and holidays from the organisers' dev pack.">{canAdmin && <Button disabled={m.pending || demo} onClick={() => void run()}><Download size={14} />{m.pending ? 'Importing bundle…' : 'Import official bundle'}</Button>}</PanelTitle>
    {m.pending && <p role="status" className="muted-note">Parsing documents, clauses, relations, ledger and holidays. This can take a minute.</p>}<MutationFeedback mutation={m} />
    {result !== null && <div className="bundle-summary">{bundleSummary(result).map(s => <div key={s.label}><strong>{s.value}</strong><small>{s.label}</small></div>)}</div>}
    {warnings.length > 0 && <details><summary>{warnings.length} import warning{warnings.length === 1 ? '' : 's'}</summary><ul>{warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></details>}
    {canAdmin && !demo && <div className="button-row"><Button variant="secondary" disabled={m.pending} onClick={() => void verifySaved()}>Recheck saved citations</Button>{recheck && <p role="status">{text(recheck.verified, '0')} verified; {text(recheck.repaired, '0')} source quotations restored; {text(recheck.unverified, '0')} still need review.</p>}</div>}
    <LedgerHolidays /></Panel>;
}
const flagged = (r: ApiRecord) => r.late === true || r.unpaid === true || ['late', 'unpaid', 'overdue', 'missed'].includes(text(r.status, '').toLowerCase()) || Boolean(r.flag);
export function LedgerHolidays() {
  const ledger = useResource('/api/ledger'); const holidays = useResource('/api/holidays');
  const rows = list(ledger.data, 'ledger').length ? list(ledger.data, 'ledger') : list(ledger.data, 'rows').length ? list(ledger.data, 'rows') : list(ledger.data);
  const hol = list(holidays.data, 'holidays').length ? list(holidays.data, 'holidays') : list(holidays.data);
  if (ledger.error && holidays.error) return null;
  return <details className="ledger-holidays"><summary>Payments ledger ({rows.length}) and holidays ({hol.length})</summary>
    <ResourceState resource={ledger} empty={ledger.data !== undefined && !rows.length}><div className="table-scroll"><table className="data-table"><thead><tr>{['date', 'from', 'to', 'amount', 'reference', 'contract', 'status'].map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((r, i) => <tr key={i} className={flagged(r) ? 'ledger-flagged' : ''}><td>{dateText(r.date)}</td><td>{text(r.from, '')}</td><td>{text(r.to, '')}</td><td>{text(r.amount, '')} {text(r.currency, '')}</td><td>{text(r.reference, '')}</td><td>{text(r.contract_id ?? r.contract_external_id, '')}</td><td>{flagged(r) ? <Badge tone="red">{text(r.status, 'flagged')}</Badge> : text(r.status, '')}</td></tr>)}</tbody></table></div></ResourceState>
    <h4>Holidays (business-day calculations)</h4>{hol.length > 0 && <RecordTable rows={hol} columns={['date', 'name', 'observed_by']} />}</details>;
}
