'use client';
import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useResource } from '@/lib/use-resource';
import { useClauseTypes } from '@/lib/use-clause-types';
import { clauseTypeKey, dateText, formatMoney, list, query, record, text } from '@/lib/api';
import { useWorkspace } from './providers';
import { PageTitle, Panel, PanelTitle, Button } from './ui';
import { CitationChip, DownloadLink, MutationFeedback, ResourceState, SourceBadge, Status, useMutation } from './api-ui';
import { ClockControl } from './clock-control';
function OwnerEditor({ entry }: { entry: Record<string,unknown> }) {
 const [owner,setOwner] = useState(text(entry.owner,'')); const m = useMutation(); const { canAdmin } = useWorkspace();
 return <form onSubmit={e => { e.preventDefault(); void m.run('/api/owners',{ timeline_id: entry.id,owner }); }}><input className="input" aria-label="Assigned owner" value={owner} onChange={e => setOwner(e.target.value)} disabled={!canAdmin || m.pending} />{canAdmin && <Button variant="ghost" disabled={m.pending || !owner.trim()}>Save</Button>}<MutationFeedback mutation={m} /></form>;
}
export function TimelineView() {
 const { date } = useWorkspace(); const search = useSearchParams(); const contract = search.get('contract_id') ?? ''; const clauseType = search.get('clause_type') ?? ''; const month = search.get('month') ?? '';
 const r = useResource(query('/api/timeline',{ as_of: date,contract_id: contract || undefined }),180);
 const allEntries = list(record(r.data).entries);
 const types = useClauseTypes(allEntries.map(e => text(e.contract_id ?? record(e.citation).contract_id,'')).filter(Boolean),Boolean(clauseType));
 const entries = allEntries.filter(e => (!clauseType || types.index[clauseTypeKey(e.contract_id ?? record(e.citation).contract_id,record(e.citation).clause_number)] === clauseType.toLowerCase()) && (!month || text(e.date,'').startsWith(month)));
 const resource = {...r,data:types.loading&&!Object.keys(types.index).length?undefined:r.data,loading:r.loading||types.loading,error:r.error||types.error,reload:()=>{r.reload();types.reload();}};
 return <><PageTitle eyebrow="OBLIGATION TIMELINE" title="See what comes next." description="Deadlines, risks and costs returned for your selected date."><DownloadLink path="/api/export/calendar.ics">Export calendar</DownloadLink></PageTitle><ClockControl /><Panel><PanelTitle title="Upcoming and missed obligations" description={[contract,clauseType,month].filter(Boolean).join(' · ') || 'All contracts'}><SourceBadge value="analysis" /></PanelTitle><ResourceState resource={resource} empty={!resource.loading && r.data !== undefined && !entries.length}><div className="table-scroll"><table className="data-table"><thead><tr><th>Date</th><th>Obligation</th><th>Status</th><th>Amount</th><th>Reference</th><th>Owner</th></tr></thead><tbody>{entries.map((e,i) => <tr key={text(e.id,String(i))}><td>{dateText(e.date)}</td><td><strong>{text(e.title)}</strong><small>{text(e.kind)}</small><SourceBadge value={e.source} /></td><td><Status value={e.status} /></td><td>{formatMoney(e.amount)}</td><td><CitationChip value={e.citation} /></td><td><OwnerEditor entry={e} /></td></tr>)}</tbody></table></div></ResourceState></Panel><p className="muted-note">Amounts and deadline states are supplied by the backend. Select a different date to request updated projections.</p></>;
}
