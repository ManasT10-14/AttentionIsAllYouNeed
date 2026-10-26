'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Mail, Cpu, ScrollText, Phone, Play, StepForward, FastForward, RotateCcw, Inbox, type LucideIcon } from 'lucide-react';
import { useResource } from '@/lib/use-resource';
import { dateText, dateTimeText, list, query, record, text, type ApiRecord } from '@/lib/api';
import { checkpointsOf, compareSnapshots, eventFeed, trackPosition, CHANNEL_LABEL, type SimEvent } from '@/lib/odin';
import { useWorkspace } from './providers';
import { Badge, Button, PageTitle, Panel, PanelTitle } from './ui';
import { FieldValue, MutationFeedback, ResourceState, Status, useMutation } from './api-ui';
import { BundlePanel, LedgerHolidays } from './bundle-panel';

const CHANNEL_ICON: Record<string, LucideIcon> = { email: Mail, system: Cpu, status_log: ScrollText, phone: Phone };
const DROPS = [{ n: 1, label: 'Drop 1', range: 'E-01 to E-10' }, { n: 2, label: 'Drop 2', range: 'E-11 to E-18' }];

export function SimulationView() {
  const { canAdmin, demo, refresh } = useWorkspace(); const m = useMutation();
  const sim = useResource('/api/simulation'); const events = useResource('/api/events'); const snaps = useResource('/api/simulation/checkpoints');
  const s = record(sim.data); const now = text(s.sim_now ?? s.current_date ?? record(s.clock).sim_now, ''); const start = text(s.start_date ?? s.start, '');
  const checkpoints = checkpointsOf(s, now); const end = checkpoints[checkpoints.length - 1]?.date ?? now;
  const loaded = new Set((Array.isArray(s.drops_loaded) ? s.drops_loaded : []).map(d => text(record(d).drop ?? record(d).n ?? d, '')));
  const next = checkpoints.find(c => !c.reached);
  const initialized = s.initialized !== false && Boolean(start);
  const baseDisabled = m.pending || demo || !canAdmin || !initialized;
  const disabled = baseDisabled || Boolean(s.running);
  const loadDisabled = baseDisabled || Boolean(s.simulation_running);
  useEffect(() => { if (!s.running) return; const timer = setInterval(refresh, 3000); return () => clearInterval(timer); }, [s.running, refresh]);
  const feed = eventFeed(Array.isArray(events.data) ? events.data : record(events.data).events);
  const [advance, setAdvance] = useState('');
  const act = (path: string, body?: unknown) => void m.run('/api/simulation' + path, body);
  return <>
    <PageTitle eyebrow="SIMULATION" title="Replay the quarters." description="Load the official event drops, move the simulated clock to each checkpoint and inspect what Odin did at every step.">
      {canAdmin && <Button variant="ghost" disabled={disabled} onClick={() => act('/reset')}><RotateCcw size={14} />Reset</Button>}</PageTitle>
    <MutationFeedback mutation={m} />
    {demo && <p className="report-notice">This is the frontend preview. <Link className="text-link" href="/auth/sign-in">Sign in to a connected workspace</Link> to import and replay the official event drops.</p>}
    {!demo && sim.data !== undefined && !initialized && <BundlePanel onImported={() => refresh()} />}
    {!canAdmin && !demo && <p className="muted-note">An administrator can load drops and advance the simulation. Your access is read-only.</p>}
    {Boolean(s.running) && <p role="status" className="muted-note">Odin is processing the current run. You can load drops while analysis runs; replay starts after analysis finishes. <Link className="text-link" href="/dashboard/workflow">View running tasks</Link></p>}
    {text(record(s.last_run).error, '') && <p role="alert" className="form-error">{text(record(s.last_run).error)}</p>}
    <ResourceState resource={sim}>
      <Panel><PanelTitle title="Clock" description={now ? 'Simulated date ' + dateText(now) : 'No simulation state yet. Import the official bundle first.'} />
        <div className="sim-track" role="img" aria-label={'Clock from ' + dateText(start) + ' to ' + dateText(end) + ', now ' + dateText(now)}>
          <i className="sim-line" />
          {[{ date: start, label: 'Start', reached: true }, ...checkpoints.map(c => ({ date: c.date, label: c.label, reached: c.reached }))].filter(p => p.date).map(p => <span key={p.label} className={'sim-mark' + (p.reached ? ' reached' : '')} style={{ left: trackPosition(p.date, start, end) + '%' }}><b>{p.label}</b><small>{dateText(p.date)}</small></span>)}
          {now && <span className="sim-now" style={{ left: trackPosition(now, start, end) + '%' }} title={'Now ' + dateText(now)}><small>Now</small></span>}
        </div>
        <div className="button-row sim-controls">
          <Button disabled={disabled || !next} onClick={() => act('/play', { until: next?.date })}><Play size={14} />Play to next checkpoint{next ? ' (' + dateText(next.date) + ')' : ''}</Button>
          <Button variant="secondary" disabled={disabled || !loaded.size || Number(s.pending_events) === 0} onClick={() => act('/step')}><StepForward size={14} />Step one event</Button>
          <label className="sim-advance"><input className="input" type="date" aria-label="Advance to date" value={advance} min={start || undefined} onChange={e => setAdvance(e.target.value)} /><Button variant="secondary" disabled={disabled || !advance} onClick={() => act('/advance', { to: advance })}><FastForward size={14} />Advance to</Button></label>
        </div>
        {demo && <p className="muted-note">Simulation controls need a connected backend.</p>}
      </Panel>
    </ResourceState>
    <div className="sim-drops">{DROPS.map(d => <Panel key={d.n} className="sim-drop"><PanelTitle title={d.label} description={d.range}><Badge tone={loaded.has(String(d.n)) ? 'green' : 'neutral'}>{loaded.has(String(d.n)) ? 'Loaded' : 'Not loaded'}</Badge></PanelTitle>
      <div className="button-row"><Button variant="secondary" disabled={loadDisabled || loaded.has(String(d.n)) || (d.n === 2 && !loaded.has("1"))} onClick={() => act('/drops/' + d.n + '/load')}>Load</Button><Button variant="ghost" disabled={disabled || !loaded.size || Number(s.pending_events) === 0} onClick={() => act('/step')}>Step</Button><Button variant="ghost" disabled={disabled || !next} onClick={() => act('/play', { until: next?.date })}>Play to checkpoint</Button></div></Panel>)}
      <Panel className="sim-gmail"><PanelTitle title="External events via Gmail" description="Beyond the official drops" /><p>Real emails sent to the company inbox are ingested and processed exactly like drop events: matched to contracts, assessed against clauses and turned into alerts and drafted actions.</p><Link className="text-link" href="/dashboard/events"><Inbox size={14} /> Open Events and Inbox</Link></Panel></div>
    <Panel><PanelTitle title="Event feed" description={feed.length + ' events in timestamp order'} />
      <ResourceState resource={events} empty={events.data !== undefined && !feed.length}><ol className="sim-feed">{feed.map((e, i) => <FeedRow key={e.id || i} e={e} />)}</ol></ResourceState></Panel>
    <Checkpoints resource={snaps} start={start} />
    <Panel><PanelTitle title="Payments and holidays" description="Late or unpaid rows are highlighted." /><LedgerHolidays /></Panel>
  </>;
}
function FeedRow({ e }: { e: SimEvent }) {
  const Icon = CHANNEL_ICON[e.channel] ?? Mail; const [open, setOpen] = useState(false);
  const impact = useResource(open && e.id ? '/api/reports/events/' + encodeURIComponent(e.id) : null); const d = record(impact.data);
  const malformed = e.status === 'rejected' && !e.timestamp;
  return <li className={'sim-event sim-' + (e.status || 'unknown')}><span className="sim-channel" title={CHANNEL_LABEL[e.channel] ?? e.channel}><Icon size={16} /></span>
    <div><strong>{e.external_id && <code className="external-id">{e.external_id}</code>} {e.subject || (malformed ? 'Malformed line' : 'Untitled')}</strong>
      <small>{e.timestamp ? dateTimeText(e.timestamp) : 'No timestamp'}{e.sender || e.recipient ? ' · ' + (e.sender || '?') + ' to ' + (e.recipient || '?') : ''}{e.source ? ' · ' + e.source : ''}{e.line !== undefined ? ' · line ' + e.line : ''}</small>
      <span className="button-row"><Status value={e.status} />{e.reason && <span className="muted-note">{e.reason}</span>}</span>
      {e.id && <span className="button-row"><Link className="text-link" href={query('/dashboard/workflow', { event: e.id })}>Workflow</Link><button className="text-link" onClick={() => setOpen(v => !v)}>{open ? 'Hide impact' : 'Impact'}</button></span>}
      {open && <ResourceState resource={impact}><small>{['alerts', 'actions', 'violations'].map(k => k + ': ' + list(d[k]).length).join(' · ')}</small></ResourceState>}</div></li>;
}
function Checkpoints({ resource, start }: { resource: { loading: boolean; error: string; reload: () => void; data?: unknown }; start: string }) {
  const rows = (Array.isArray(resource.data) ? list(resource.data) : list(resource.data, 'checkpoints')).sort((a, b) => text(a.checkpoint ?? a.date, '').localeCompare(text(b.checkpoint ?? b.date, '')));
  const [a, setA] = useState(''); const [b, setB] = useState('');
  const key = (r: ApiRecord) => text(r.checkpoint ?? r.date, ''); const find = (k: string) => rows.find(r => key(r) === k);
  const A = find(a), B = find(b);
  return <Panel><PanelTitle title="Checkpoints" description={start ? 'Snapshots as of each checkpoint, starting ' + dateText(start) : 'Snapshots as of each checkpoint'} />
    <ResourceState resource={resource} empty={resource.data !== undefined && !rows.length}>
      <div className="sim-checkpoints">{rows.map(r => <details key={key(r)}><summary><strong>{dateText(key(r))}</strong> {['obligations', 'deadlines', 'open_risks', 'actions'].map(k => <Badge key={k}>{k.replace('_', ' ')} {Array.isArray(r[k]) ? (r[k] as unknown[]).length : text(r[k], '0')}</Badge>)}</summary>
        <div className="detail-list">{['obligations', 'deadlines', 'exposure', 'open_risks', 'actions'].map(k => <div key={k}><span>{k.replace('_', ' ')}</span><FieldValue value={r[k]} /></div>)}</div>
        {r.analysis_complete === false && <p className="muted-note">Analysis is incomplete. This snapshot preserves available evidence and must be reviewed.</p>}{r.report_md ? <pre className="template-text">{text(r.report_md)}</pre> : null}</details>)}</div>
      {rows.length > 1 && <div className="sim-compare"><h3>Compare checkpoints</h3><div className="button-row">{[[a, setA], [b, setB]].map(([v, set], i) => <select key={i} className="compact-select" aria-label={'Checkpoint ' + (i ? 'B' : 'A')} value={v as string} onChange={e => (set as (x: string) => void)(e.target.value)}><option value="">Select…</option>{rows.map(r => <option key={key(r)} value={key(r)}>{dateText(key(r))}</option>)}</select>)}</div>
        {A && B && <div className="table-scroll"><table className="data-table"><thead><tr><th>Measure</th><th>{dateText(a)}</th><th>{dateText(b)}</th><th>Change</th></tr></thead><tbody>{compareSnapshots(A, B).map(c => <tr key={c.key}><td>{c.key.replace('_', ' ')}</td><td>{c.a}</td><td>{c.b}</td><td>{c.delta > 0 ? '+' : ''}{c.delta}</td></tr>)}</tbody></table></div>}</div>}
    </ResourceState></Panel>;
}
