'use client';
import { useMemo, useState } from 'react';
import { ArrowRight, PenLine } from 'lucide-react';
import { useResource } from '@/lib/use-resource';
import { dateText, formatMoney, list, record, text, type ApiRecord } from '@/lib/api';
import { wordDiff } from '@/lib/word-diff';
import { CitationChip, Status } from './api-ui';
import '@/app/insights-views.css';

function Redline({ before, after, mode }: { before: string; after: string; mode: 'inline' | 'side' }) {
  const parts = useMemo(() => wordDiff(before, after), [before, after]);
  if (mode === 'side') return <div className="am-side"><div><small>Current wording</small><p>{parts.filter(p => p.k !== '+').map((p, i) => p.k === '-' ? <del key={i}>{p.t}</del> : p.t)}</p></div><ArrowRight size={16} aria-hidden /><div><small>Proposed wording</small><p>{parts.filter(p => p.k !== '-').map((p, i) => p.k === '+' ? <ins key={i}>{p.t}</ins> : p.t)}</p></div></div>;
  return <p className="am-inline">{parts.map((p, i) => p.k === '-' ? <del key={i}>{p.t}</del> : p.k === '+' ? <ins key={i}>{p.t}</ins> : p.t)}</p>;
}
const money = (v: unknown) => { const r = record(v); return typeof v === 'number' ? v : typeof r.amount === 'number' ? r.amount : undefined; };

/** Full amendment view for the action review sheet. */
export function AmendmentDetail({ action }: { action: ApiRecord }) {
  const [mode, setMode] = useState<'inline' | 'side'>('inline');
  const contractId = text(action.contract_id, '');
  const contract = useResource(contractId ? '/api/contracts/' + encodeURIComponent(contractId) : null);
  const headings = new Map(list(record(contract.data).clauses).map(c => [text(c.number), text(c.heading, '')]));
  const headingOf = (n: string) => headings.get(n) || headings.get(n.split('.')[0]) || '';
  const redlines = list(action.redlines); const cites = list(action.citations);
  const currency = text(record(action.est_exposure_avoided).currency, text(record(action.counterfactual).currency, ''));
  const avoided = money(action.est_exposure_avoided) ?? money(record(action.counterfactual).avoided);
  const cf = record(action.counterfactual);
  const approval = action.status === 'approved' || action.status === 'applied' ? 'Approved by ' + text(action.approved_by, 'a reviewer') + (action.approved_at ? ' on ' + dateText(action.approved_at) : '') : action.status === 'rejected' ? 'Rejected' : (action.needs_approval ?? action.needs_human_approval) === false ? 'No approval needed' : 'Awaiting approval before it can be applied';
  return <section className="am" aria-label="Proposed amendment">
    <div className="am-summary">
      <div><span>Status</span><Status value={action.status} /></div>
      <div><span>Approval</span><strong>{approval}</strong></div>
      <div><span>Changes</span><strong>{redlines.length} clause{redlines.length === 1 ? '' : 's'}</strong></div>
      {action.deadline ? <div><span>Decide by</span><strong>{dateText(action.deadline)}</strong></div> : null}
      {typeof action.confidence === 'number' ? <div><span>Confidence</span><strong>{Math.round(action.confidence * 100)}%</strong></div> : null}
    </div>
    {(avoided !== undefined || cf.without_action !== undefined) && <div className="am-impact"><h4>Expected impact</h4>
      {avoided !== undefined && <p><strong>{avoided > 0 ? formatMoney(avoided, currency) : 'No measurable change'}</strong> {avoided > 0 ? 'of exposure avoided if applied' : 'in modelled exposure from this change alone'}</p>}
      {cf.without_action !== undefined && <p className="am-flow">Worst-case exposure <b>{formatMoney(cf.without_action, currency)}</b> <ArrowRight size={13} aria-hidden /> <b>{formatMoney(cf.with_action, currency)}</b> after the amendment</p>}
    </div>}
    <div className="am-bar"><h4>What changes</h4><div className="segmented-control" role="group" aria-label="Redline layout"><button className={mode === 'inline' ? 'active' : ''} aria-pressed={mode === 'inline'} onClick={() => setMode('inline')}>Inline</button><button className={mode === 'side' ? 'active' : ''} aria-pressed={mode === 'side'} onClick={() => setMode('side')}>Side by side</button></div></div>
    {!redlines.length && <p className="muted-note">This amendment has no clause-level redlines; see the drafted letter above.</p>}
    {redlines.map((r, i) => { const n = text(r.clause_number, '?'); const cs = cites.filter(c => text(c.clause_number) === n); return <article className="am-clause" key={i}>
      <header><PenLine size={14} aria-hidden /><h5>Clause {n}{headingOf(n) ? ' · ' + headingOf(n) : ''}</h5></header>
      {text(r.reason, '') && <p className="am-why"><b>Why:</b> {text(r.reason)}</p>}
      <Redline before={text(r.before, '')} after={text(r.after, '')} mode={mode} />
      <div className="citation-list">{(cs.length ? cs : [{ contract_id: contractId, clause_number: n }]).map((c, k) => <CitationChip key={k} value={c} />)}</div>
    </article>; })}
    {list(action.related_finding_ids).length > 0 && <p className="muted-note">Addresses {list(action.related_finding_ids).length} finding{list(action.related_finding_ids).length === 1 ? '' : 's'}: {(action.related_finding_ids as string[]).join(', ')}</p>}
  </section>;
}

/** Compact one-glance version for queue rows and alert cards. */
export function AmendmentSummary({ action, onOpen }: { action: ApiRecord; onOpen?: () => void }) {
  const redlines = list(action.redlines); const first = redlines[0];
  if (!first) return null;
  return <div className="am-mini"><span><PenLine size={12} aria-hidden /> Clause {text(first.clause_number)}{redlines.length > 1 ? ' +' + (redlines.length - 1) + ' more' : ''}</span>{text(first.reason, '') && <small>{text(first.reason)}</small>}{onOpen && <button className="text-link" onClick={onOpen}>Review amendment</button>}</div>;
}
