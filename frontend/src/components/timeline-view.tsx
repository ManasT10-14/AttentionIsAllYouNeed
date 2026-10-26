'use client';
import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useResource } from '@/lib/use-resource';
import { useClauseTypes } from '@/lib/use-clause-types';
import { clauseTypeKey, dateText, formatMoney, list, query, record, text, type ApiRecord } from '@/lib/api';
import { useWorkspace } from './providers';
import { PageTitle, Panel, PanelTitle, Button, Badge } from './ui';
import { CitationChip, DownloadLink, MutationFeedback, ResourceState, SourceBadge, Status, useMutation } from './api-ui';
import { ClockControl } from './clock-control';

function OwnerEditor({ entry }: { entry: ApiRecord }) {
 const [owner,setOwner] = useState(text(entry.owner,'')); const m = useMutation(); const { canAdmin } = useWorkspace();
 return <form onSubmit={e => { e.preventDefault(); void m.run('/api/owners',{ timeline_id: entry.id,owner }); }}><input className="input" aria-label="Assigned owner" value={owner} onChange={e => setOwner(e.target.value)} disabled={!canAdmin || m.pending} />{canAdmin && <Button variant="ghost" disabled={m.pending}>Save</Button>}<MutationFeedback mutation={m} /></form>;
}

type View = 'all' | 'history' | 'due' | 'upcoming' | 'worst';
const VIEWS: {key: View; label: string}[] = [{key:'all',label:'All obligations'},{key:'history',label:'Past commitments & payments'},{key:'due',label:'Due & missed'},{key:'upcoming',label:'Upcoming'},{key:'worst',label:'If no action'}];

export function TimelineView() {
 const { date } = useWorkspace(); const search = useSearchParams();
 const contract = search.get('contract_id') ?? ''; const clauseType = search.get('clause_type') ?? ''; const month = search.get('month') ?? '';
 const [view,setView] = useState<View>('all'); const [kind,setKind] = useState(''); const [from,setFrom] = useState(''); const [to,setTo] = useState('');
 const r = useResource(query('/api/timeline',{ as_of: date,contract_id: contract || undefined }),180);
 const data = record(r.data); const allEntries = list(data.entries); const history = list(data.history); const projections = list(data.projections);
 const types = useClauseTypes(allEntries.map(e => text(e.contract_id ?? record(e.citation).contract_id,'')).filter(Boolean),Boolean(clauseType));
 const candidates = view === 'history' ? [...allEntries.filter(e => text(e.date,'') < date), ...history] : view === 'worst' ? projections : allEntries;
 const entries = candidates.filter(e => {
   const day = text(e.date,'');
   return (!clauseType || types.index[clauseTypeKey(e.contract_id ?? record(e.citation).contract_id,record(e.citation).clause_number)] === clauseType.toLowerCase())
    && (!month || day.startsWith(month)) && (!kind || e.kind === kind) && (!from || day >= from) && (!to || day <= to)
    && (view !== 'due' || ['due','missed'].includes(text(e.status,'')))
    && (view !== 'upcoming' || (day > date && !['done','missed'].includes(text(e.status,''))));
 }).sort((a,b) => text(a.date,'').localeCompare(text(b.date,'')));
 const resource = {...r,loading:r.loading||types.loading,error:r.error||types.error,reload:()=>{r.reload();types.reload();}};
 const missing = Array.isArray(data.unanalysed_contracts) ? data.unanalysed_contracts.map(String) : [];
 return <>
  <PageTitle eyebrow="OBLIGATION TIMELINE" title="See what comes next." description="Past commitments, current obligations and the cost of taking no action, at the selected simulated date."><DownloadLink path="/api/export/calendar.ics">Export calendar</DownloadLink></PageTitle>
  <ClockControl />
  {missing.length > 0 && <p className="report-notice">Timeline coverage is incomplete. These documents still need extraction: {missing.join(', ')}. Missing deadlines and exposure are unknown.</p>}
  <div className="button-row" role="group" aria-label="Timeline view">{VIEWS.map(v => <Button key={v.key} variant={view === v.key ? 'primary' : 'secondary'} aria-pressed={view === v.key} onClick={() => setView(v.key)}>{v.label}</Button>)}</div>
  <Panel><PanelTitle title={VIEWS.find(v => v.key === view)?.label ?? 'Timeline'} description={[contract,clauseType,month].filter(Boolean).join(' · ') || 'All contracts'}><Badge>{entries.length} entries</Badge></PanelTitle>
   <div className="button-row"><label>Type <select className="compact-select" aria-label="Obligation type" value={kind} onChange={e => setKind(e.target.value)}><option value="">All types</option>{['payment','obligation','renewal','notice_deadline','expiry','penalty_trigger'].map(k => <option key={k} value={k}>{k.replaceAll('_',' ')}</option>)}</select></label><label>From <input className="input" type="date" aria-label="Timeline from date" value={from} onChange={e => setFrom(e.target.value)} /></label><label>To <input className="input" type="date" aria-label="Timeline to date" value={to} min={from || undefined} onChange={e => setTo(e.target.value)} /></label></div>
   {view === 'history' && <p className="muted-note">Ledger entries are recorded payment facts. Scheduled commitments are shown separately; a past due date alone does not prove payment or breach.</p>}
   {view === 'worst' && <p className="muted-note">Conditional scenarios, not confirmed breaches. Each amount uses stated contract numbers; see the assumptions below. A projected month is a scenario horizon, not a new contractual due date.</p>}
   <ResourceState resource={resource} empty={!resource.loading && r.data !== undefined && !entries.length}>
    <div className="table-scroll"><table className="data-table"><thead><tr><th>Date</th><th>Contract</th><th>Obligation / fact</th><th>Status</th><th>Amount</th><th>Evidence</th><th>Owner</th></tr></thead><tbody>{entries.map((e,i) => <tr key={text(e.id,String(i))}><td>{dateText(e.date)}</td><td>{text(e.contract_id,'')}</td><td><strong>{text(e.title)}</strong><small>{text(e.kind)}</small><SourceBadge value={e.source} /></td><td><Status value={e.status} /></td><td>{formatMoney(e.amount)}</td><td>{e.source === 'ledger' ? <span>Payments ledger<br />{text(e.from,'')} → {text(e.to,'')}</span> : <CitationChip value={e.citation} />}</td><td>{e.source === 'ledger' || e.scenario === 'worst_case' ? '—' : <OwnerEditor entry={e} />}</td></tr>)}</tbody></table></div>
   </ResourceState>
  </Panel>
  {view === 'worst' && <Panel><PanelTitle title="Financial projection and assumptions" description="Expected and worst-case values stay separate for each contract and currency." /><div className="table-scroll"><table className="data-table"><thead><tr><th>Contract</th><th>Expected</th><th>Worst case</th><th>Assumptions</th></tr></thead><tbody>{list(data.contracts).map(c => {const x=record(c.exposure);return <tr key={text(c.contract_id)}><td>{text(c.contract_id)}</td><td>{formatMoney({amount:x.expected,currency:x.currency})}</td><td>{formatMoney({amount:x.worst_case,currency:x.currency})}</td><td>{Array.isArray(x.assumptions) ? x.assumptions.map((a,i) => <p key={i}>{String(a)}</p>) : 'No assumptions recorded'}</td></tr>;})}</tbody></table></div></Panel>}
 </>;
}
