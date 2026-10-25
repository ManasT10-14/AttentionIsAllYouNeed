'use client';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { dateText, dateTimeText, formatMoney, list, query, record, text } from '@/lib/api';
import { useResource } from '@/lib/use-resource';
import { missingReportExplanation } from '@/lib/review-data';
import { reportRuns, runReportTarget, runTitle } from '@/lib/run-presentation';
import { useWorkspace } from './providers';
import { Button,Badge,PageTitle,Panel,PanelTitle } from './ui';
import { CitationChip,DownloadLink,FieldValue,MutationFeedback,ResourceState,SourceBadge,Status,useMutation } from './api-ui';

const TABS = [['runs', 'Workflow reports'], ['contracts', 'By contract'], ['events', 'By event']] as const;
type Tab = typeof TABS[number][0];
type Row = Record<string, unknown>;

function Refs({ value }: { value: unknown }) {
 const refs = list(value);
 return <section><h3>References</h3>{refs.map((ref, i) => <div key={i}><CitationChip value={ref} /><blockquote className="source-quote">{text(ref.quote, '')}</blockquote></div>)}{!refs.length && <p className="muted-note">No references returned.</p>}</section>;
}
function Body({ report }: { report: Row }) {
 return <>{Object.entries(report).filter(([k]) => !['references', 'state'].includes(k)).map(([k, v]) => <section key={k}><h3>{k.replaceAll('_', ' ')}</h3><FieldValue value={v} /></section>)}<Refs value={report.references} /></>;
}
const Items = ({ title, rows, label }: { title: string; rows: unknown; label: (r: Row) => string }) => <section><h3>{title} ({list(rows).length})</h3>{list(rows).length ? <ul>{list(rows).map((r, i) => <li key={i}>{label(r)}</li>)}</ul> : <p className="muted-note">None</p>}</section>;

function RunReport({ id, title }: { id: string; title: string }) {
 const r = useResource('/api/reports/runs/' + encodeURIComponent(id)); const d = record(record(r.data).diff); const rep = record(record(r.data).report); const ex = record(d.exposure_delta);
 const claim = (x: Row) => text(x.contract_id, '') + ': ' + text(x.claim ?? x.subject, '');
 const prev = text(record(r.data).previous_run_id, '');
 return <ResourceState resource={r}>{r.data !== undefined && <div className="report-content">
  <PanelTitle title={title} description={dateText(record(r.data).generated_at)}><SourceBadge value="analysis" /><DownloadLink path={'/api/reports/runs/' + id + '?format=pdf'}>Download PDF</DownloadLink></PanelTitle>
  <p><Link className="text-link" href={query('/dashboard/workflow', { run: id })}>View workflow execution</Link></p>
  <section className="report-completeness"><h3>What changed since {prev ? 'run ' + prev.slice(0, 8) : 'start (first run)'}</h3>
   {d.exposure_delta ? <p>Exposure change: expected {formatMoney(ex.expected, text(ex.currency, 'INR'))}, worst case {formatMoney(ex.worst_case, text(ex.currency, 'INR'))}</p> : null}
   <Items title="New findings" rows={d.new_findings} label={claim} /><Items title="Resolved findings" rows={d.resolved_findings} label={claim} />
   <Items title="New actions" rows={d.new_actions} label={claim} /><Items title="Resolved actions" rows={d.resolved_actions} label={claim} /></section>
  <h2>Final company report</h2><Body report={rep} /></div>}</ResourceState>;
}
function SelectedRunReport({ id, snapshot, title }: { id: string; snapshot: boolean; title: string }) {
 const workflow = useResource(snapshot ? null : '/api/workflow/' + encodeURIComponent(id));
 if (snapshot) return <RunReport id={id} title={title} />;
 const w = record(workflow.data); const target = runReportTarget(w); const run = record(w.run); const remarks = record(w.remarks);
 return <ResourceState resource={workflow}>{workflow.data !== undefined && (target?.kind === 'run' ? <RunReport id={target.id} title={title} /> : target?.kind === 'event' ? <EventReport id={target.id} /> : <div className="report-content execution-report">
  <PanelTitle title={title} description={dateTimeText(run.started_at)}><Status value={run.status} /></PanelTitle>
  <div className="report-availability"><h3>{run.status === 'running' ? 'Analysis is still in progress' : 'Recorded execution summary'}</h3><p>{missingReportExplanation(run)}</p></div>
  <p><Link className="text-link" href={query('/dashboard/workflow', { run: id })}>Inspect the full agent workflow</Link> <Link className="text-link" href={query('/dashboard/agent-review', { run: id })}>Review agent message history</Link></p>
  {remarks.error ? <p className="form-error">{text(remarks.error)}</p> : null}
  {['finding', 'violation', 'alert', 'action'].map(kind => <section key={kind}><h3>{({ finding: 'Findings', violation: 'Violations', alert: 'Alerts', action: 'Actions' })[kind]}</h3>{list(record(w.outputs)[kind]).map(o => <article className="report-output" key={text(o.id)}><Status value={o.status} /><p>{text(o.claim ?? o.explanation ?? o.title ?? o.subject)}</p><small>{text(o.contract_id, '')}</small>{list(o.citations).map((c, i) => <CitationChip key={i} value={c} />)}</article>)}{!list(record(w.outputs)[kind]).length && <p className="muted-note">None recorded.</p>}</section>)}
  <section><h3>Remaining gaps</h3>{list(remarks.gaps).length ? <FieldValue value={remarks.gaps} /> : <p className="muted-note">No workstream gaps recorded.</p>}</section>
 </div>)}</ResourceState>;
}
function EventReport({ id }: { id: string }) {
 const r = useResource('/api/reports/events/' + encodeURIComponent(id)); const rep = record(r.data); const ev = record(rep.event); const ex = record(rep.exposure_delta); const ruling = new Map(list(rep.rulings).map(x => [text(x.finding_id), x]));
 const runIds = Array.isArray(rep.run_ids) ? (rep.run_ids as string[]) : [];
 return <ResourceState resource={r}>{r.data !== undefined && <div className="report-content">
  <PanelTitle title={'Event report · ' + text(ev.subject ?? ev.event_type)} description={dateText(ev.occurred_at) + ' · runs ' + (runIds.length ? runIds.map(x => x.slice(0, 8)).join(', ') : 'n/a')}><Status value={ev.status} /><DownloadLink path={'/api/reports/events/' + id + '?format=pdf'}>Download PDF</DownloadLink></PanelTitle>
  <p><Link className="text-link" href={query('/dashboard/workflow', { event: id })}>View workflow execution</Link></p>
  <section><h3>Affected contracts</h3>{(Array.isArray(rep.affected_contracts) ? rep.affected_contracts as string[] : []).map(c => <Link key={c} className="citation-chip" href={query('/dashboard/contracts', { contract: c })}>{c}</Link>)}</section>
  <section><h3>Exposure delta</h3><p>{rep.exposure_delta ? formatMoney(ex.amount, text(ex.currency, 'INR')) : 'No quantified exposure.'}</p></section>
  <Items title="New violations" rows={rep.violations} label={v => text(v.contract_id) + ' §' + text(v.clause_number) + ' · ' + text(v.breach_type) + ' (' + text(v.status) + '): ' + text(v.explanation, '')} />
  <Items title="Alerts" rows={rep.alerts} label={a => '[' + text(a.severity) + '] ' + text(a.title)} />
  <Items title="Actions" rows={rep.actions} label={a => text(a.kind) + ': ' + text(a.subject) + ' (' + text(a.status) + ')'} />
  <section><h3>Tyr rulings</h3>{list(rep.findings).map(f => { const ru = record(ruling.get(text(f.id))); return <p key={text(f.id)}>{text(f.claim)} <Badge tone="green">{ruling.has(text(f.id)) ? 'Tyr: ' + text(ru.winner) + ', sev ' + text(ru.final_severity) : 'no ruling'}</Badge></p>; })}{!list(rep.findings).length && <p className="muted-note">None</p>}</section>
  <Refs value={rep.affected_clauses} /></div>}</ResourceState>;
}

export function ReportsView() {
 const router = useRouter(); const p = useSearchParams(); const {canAdmin,demo}=useWorkspace(); const m=useMutation();
 const index = useResource('/api/report-index'); const idx = record(index.data);
 const recentRuns = useResource('/api/runs'); const agreements = useResource('/api/contracts'); const eventList = useResource('/api/events');
 const counterparties = useResource('/api/insights/counterparties');
 const requestedTab = p.get('tab');
 const tab = (TABS.some(([key]) => key === requestedTab) ? requestedTab as Tab : null) || (p.get('event') ? 'events' : p.get('contract') ? 'contracts' : 'runs');
 const go = (t: Tab, key: string, value: string) => router.push(query('/dashboard/reports', { tab: t, [key]: value }));
 const runs = reportRuns(list(idx.runs), list(recentRuns.data)), contracts = list(idx.contracts), events = list(idx.events);
 const titleFor = (r: Row) => runTitle(r, list(agreements.data), list(eventList.data));
 const run = p.get('run') || text(runs[0]?.run_id, ''); const event = p.get('event') || text(events[0]?.event_id, ''); const contract = p.get('contract') || 'company';
 const cpath = contract === 'company' ? '/api/reports/company' : query('/api/reports/contract', { contract_id: contract });
 const cr = useResource(tab === 'contracts' ? cpath : null);
 const row = (key: string, id: string, sel: string, t: Tab, title: string, sub: string, badge?: unknown) => <button key={id} className="inbox-event-row" aria-current={id === sel} onClick={() => go(t, key, id)}><span className="inbox-event-summary"><strong>{title}{id === sel ? ' (open)' : ''}</strong><small>{sub}</small></span>{badge ? <Status value={badge} /> : null}</button>;
 return <><PageTitle eyebrow="REPORTS" title="The complete picture." description="Workflow, contract and event reports, newest first. Each is readable here with citations and downloadable as PDF.">{canAdmin && <Button disabled={m.pending || demo} onClick={()=>void m.run('/api/reports/refresh')}>Regenerate reports</Button>}</PageTitle><MutationFeedback mutation={m} />
 <div className="segmented-control detail-tabs">{TABS.map(([k, label]) => <button key={k} className={tab === k ? 'active' : ''} onClick={() => router.push(query('/dashboard/reports', { tab: k }))}>{label}</button>)}</div>
 <div className="master-detail-layout reports-layout"><aside className="master-list"><Panel><ResourceState resource={index}><div className="inbox-event-list">
  {tab === 'runs' && <ResourceState resource={recentRuns}>{runs.map(r => row('run', text(r.run_id), run, 'runs', titleFor(r), dateTimeText(r.started_at ?? r.generated_at) + ' · ' + text(r.run_id).slice(0, 8) + (r.has_snapshot ? ' · Saved report' : ' · Execution & available reports'), r.status ?? r.completeness))}</ResourceState>}
  {tab === 'contracts' && <>{row('contract', 'company', contract, 'contracts', 'Company report (latest)', 'All contracts')}{contracts.map(c => row('contract', text(c.contract_id), contract, 'contracts', text(c.title ?? c.contract_id), 'v' + text(c.version) + ' · ' + dateText(c.generated_at) + (c.run_id ? ' · run ' + text(c.run_id).slice(0, 8) : ''), c.completeness))}</>}
  {tab === 'events' && events.map(e => row('event', text(e.event_id), event, 'events', text(e.subject ?? e.event_type), dateText(e.date) + ' · ' + (Array.isArray(e.contract_ids) ? e.contract_ids.length : 0) + ' contract(s)' + ((Array.isArray(e.run_ids) ? e.run_ids.length : 0) ? ' · run ' + text(Array.isArray(e.run_ids) ? e.run_ids[0] : '').slice(0, 8) : ''), e.status))}
  {((tab === 'runs' && !runs.length) || (tab === 'events' && !events.length)) && <p className="muted-note">{tab === 'runs' ? 'No workflow report yet. Run an analysis or an amendment.' : 'No events yet.'}</p>}
 </div></ResourceState></Panel></aside><div className="detail-pane"><Panel>
  {tab === 'runs' && (run ? <SelectedRunReport key={run} id={run} snapshot={runs.some(r => r.run_id === run && r.has_snapshot === true)} title={titleFor(runs.find(r => r.run_id === run) ?? {})} /> : null)}
  {tab === 'events' && (event ? <EventReport id={event} /> : null)}
  {tab === 'contracts' && <ResourceState resource={cr}>{cr.data !== undefined && <div className="report-content"><PanelTitle title={contract === 'company' ? 'Company report' : 'Contract report'}><SourceBadge value="analysis" /><DownloadLink path={cpath + (cpath.includes('?') ? '&' : '?') + 'format=pdf'}>Download PDF</DownloadLink></PanelTitle>{contract !== 'company' && <p><Link className="text-link" href={query('/dashboard/workflow', { contract })}>View workflow execution</Link></p>}<Body report={record(cr.data)} /></div>}</ResourceState>}
 </Panel></div></div>
 <Panel><PanelTitle title="Counterparty risk profiles" description="Exposure, violations and late-payment events by party" /><SourceBadge value="analysis" /><ResourceState resource={counterparties}><FieldValue value={counterparties.data} /></ResourceState></Panel></>;
}
