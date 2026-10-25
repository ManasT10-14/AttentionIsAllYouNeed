'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { FlaskConical, LoaderCircle } from 'lucide-react';
import { useResource } from '@/lib/use-resource';
import { dateText, list, number, record, text, type ApiRecord } from '@/lib/api';
import { useWorkspace } from './providers';
import { Badge, Button, PageTitle, Panel, PanelTitle } from './ui';
import { ResourceState, Status } from './api-ui';

const LABELS: Record<string, string> = {
  citation_faithfulness: 'Citation faithfulness', extraction_completeness: 'Extraction completeness', groundedness: 'Groundedness',
  authorized_tools: 'Authorized tools', approval_required: 'Approval enforced', forbidden_tools: 'No forbidden tools',
  tenant_isolation: 'Tenant isolation', tool_errors: 'Tool errors', max_tool_calls: 'Tool-call budget', latency: 'Latency',
  max_tokens: 'Token budget', max_cost: 'Cost budget', no_secret: 'No secret leakage', faithfulness: 'Judge: faithfulness',
  answer_relevancy: 'Judge: answer relevancy', finding_faithfulness: 'Judge: finding faithfulness',
};
const QUALITY = ['citation_faithfulness', 'extraction_completeness', 'groundedness'];
const label = (name: unknown) => LABELS[text(name, '')] ?? text(name, '').replaceAll('_', ' ');
const pct = (v: unknown) => number(v) === undefined ? '—' : Math.round((number(v) as number) * 100) + '%';
const metricOf = (run: ApiRecord, name: string) => list(run.metrics).find(m => text(m.name, '') === name);

export function Sparkline({ values, threshold }: { values: unknown; threshold?: unknown }) {
  const pts = (Array.isArray(values) ? values : []).filter((v): v is number => typeof v === 'number').slice(-30);
  if (pts.length < 2) return <span className="muted-note">{pts.length ? 'One run so far' : 'No scored runs yet'}</span>;
  const max = Math.max(1, ...pts), w = 160, h = 36;
  const xy = pts.map((v, i) => [i * (w / (pts.length - 1)), h - 2 - (v / max) * (h - 4)]);
  const t = number(threshold);
  return <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`Trend over ${pts.length} runs`}>
    {t !== undefined && t <= max && <line x1="0" x2={w} y1={h - 2 - (t / max) * (h - 4)} y2={h - 2 - (t / max) * (h - 4)} stroke="var(--chart-track)" strokeDasharray="3 3" />}
    <polyline fill="none" stroke="var(--chart-accent)" strokeWidth="1.8" points={xy.map(p => p.join(',')).join(' ')} />
    <circle cx={xy[xy.length - 1][0]} cy={xy[xy.length - 1][1]} r="2.6" fill="var(--chart-accent)" />
  </svg>;
}

function SuitePanel() {
  const { request, canAdmin, demo, refresh } = useWorkspace();
  const suites = useResource('/api/evals/suite');
  const configs = list(record(suites.data).configs);
  const jobs = list(record(suites.data).jobs);
  const [config, setConfig] = useState('offline');
  const [job, setJob] = useState<ApiRecord | null>(null);
  const [error, setError] = useState('');
  const shown = job ?? jobs[0] ?? null;
  const running = shown?.status === 'running';
  useEffect(() => {
    if (!running || !shown?.id) return;
    const timer = setInterval(() => {
      request<ApiRecord>('/api/evals/suite/' + encodeURIComponent(text(shown.id))).then(j => {
        setJob(j);
        if (j.status !== 'running') refresh();
      }).catch(() => undefined);
    }, 2000);
    return () => clearInterval(timer);
  }, [running, shown?.id, request, refresh]);
  async function start() {
    setError('');
    try { setJob(await request<ApiRecord>('/api/evals/suite', { method: 'POST', body: JSON.stringify({ config }) })); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not start the suite.'); }
  }
  const counts = record(shown?.counts);
  return <Panel>
    <PanelTitle title="Golden suite" description="Runs a ragnarok evaluation config on demand (offline and security configs make no paid model calls)">
      <div className="button-row">
        <select className="compact-select" aria-label="Suite configuration" value={config} onChange={e => setConfig(e.target.value)}>
          {(configs.length ? configs.filter(c => c.default) : [{ name: 'offline' }]).map(c => <option key={text(c.name)} value={text(c.name)}>{text(c.name)}</option>)}
        </select>
        {canAdmin && <Button disabled={running || demo} onClick={() => void start()}>{running ? <><LoaderCircle size={14} className="spin" />Running…</> : <><FlaskConical size={14} />Run golden suite</>}</Button>}
      </div>
    </PanelTitle>
    {error && <p role="alert" className="form-error">{error}</p>}
    <ResourceState resource={suites} empty={suites.data !== undefined && !shown}>
      {shown && <>
        <div className="button-row">
          <strong>{text(shown.config)}</strong><Status value={shown.status} />
          {['passed', 'failed', 'skipped', 'error', 'invalid'].map(s => number(counts[s]) ? <Badge key={s} tone={s === 'passed' ? 'green' : s === 'failed' || s === 'error' ? 'red' : 'amber'}>{counts[s] as number} {s}</Badge> : null)}
          <span className="muted-note">{dateText(shown.started_at)}{shown.report_path ? ' · report ' + text(shown.report_path) : ''}</span>
        </div>
        {shown.error ? <p role="alert" className="form-error">{text(shown.error)}</p> : null}
        {list(shown.cases).length > 0 && <div className="table-scroll"><table className="data-table">
          <thead><tr><th>Case</th><th>Kind</th><th>Checks</th></tr></thead>
          <tbody>{list(shown.cases).map(c => <tr key={text(c.case_id)}><td>{text(c.case_id)}</td><td>{text(c.kind)}</td>
            <td><div className="button-row">{list(c.checks).map((ch, i) => <span key={i} title={text(ch.reason, '')}><Status value={ch.status} /> {label(ch.name)}</span>)}</div></td></tr>)}</tbody>
        </table></div>}
      </>}
    </ResourceState>
  </Panel>;
}

export function EvalsView() {
  const summary = useResource('/api/evals/summary');
  const runs = useResource('/api/evals/runs');
  const s = record(summary.data);
  const metrics = list(s.metrics);
  const rows = list(runs.data);
  const ordered = [...metrics].sort((a, b) => (QUALITY.indexOf(text(a.name, '')) + 1 || 99) - (QUALITY.indexOf(text(b.name, '')) + 1 || 99));
  return <>
    <PageTitle eyebrow="EVALUATION" title="Measure every run." description="Each analysis, event and Ask run is scored when it finishes: citation faithfulness, extraction completeness, groundedness, tool safety and cost." />
    <ResourceState resource={summary}>
      <div className="stats-grid">
        <Panel className="stat-card"><div className="stat-heading"><span>RUNS SCORED</span></div><strong className="stat-value">{text(s.runs, '0')}</strong><p>{text(s.passed, '0')} passed · {text(s.failed, '0')} failed</p></Panel>
        <Panel className="stat-card"><div className="stat-heading"><span>MODEL SPEND</span></div><strong className="stat-value">${(number(s.usd_total) ?? 0).toFixed(3)}</strong><p>Across scored runs</p></Panel>
        <Panel className="stat-card"><div className="stat-heading"><span>LATENCY TREND</span></div><Sparkline values={list(s.latency_ms_trend).length ? s.latency_ms_trend : []} /><p>Milliseconds per run</p></Panel>
        <Panel className="stat-card"><div className="stat-heading"><span>LLM JUDGE</span></div><Badge tone={s.judge_enabled ? 'green' : 'neutral'}>{s.judge_enabled ? 'Enabled' : 'Off'}</Badge><p>DeepEval faithfulness / relevancy on Ask and sampled findings (evals.judge in odin.yaml)</p></Panel>
      </div>
      <Panel>
        <PanelTitle title="Scorecards" description="Latest score against its threshold; security checks must score 1" />
        {ordered.length ? <div className="table-scroll"><table className="data-table">
          <thead><tr><th>Metric</th><th>Latest</th><th>Threshold</th><th>Result</th><th>Pass rate</th><th>Mean</th><th>Trend</th></tr></thead>
          <tbody>{ordered.map(m => { const ms = ['latency'].includes(text(m.name, '')); return <tr key={text(m.name)}>
            <td><strong>{label(m.name)}</strong><br /><small>{text(m.category, '')} · {text(m.method, '')}</small></td>
            <td>{ms || ['max_tool_calls', 'max_tokens', 'max_cost'].includes(text(m.name, '')) ? (m.latest === 1 ? 'within' : m.latest === 0 ? 'over' : '—') : pct(m.latest)}</td>
            <td>{m.category === 'security' ? '1.0' : number(m.threshold) !== undefined ? (ms ? 'limit' : pct(m.threshold)) : '—'}</td>
            <td><Status value={m.latest_status} /></td><td>{pct(m.pass_rate)} <small>n={text(m.n, '0')}</small></td><td>{pct(m.mean)}</td>
            <td><Sparkline values={m.trend} threshold={m.category === 'security' ? undefined : m.threshold} /></td></tr>; })}</tbody>
        </table></div> : <p className="muted-note">No run has been scored yet. Run an analysis, post an event or ask a question.</p>}
      </Panel>
    </ResourceState>
    <Panel>
      <PanelTitle title="Scored runs" description="Open a run to see its workflow" />
      <ResourceState resource={runs} empty={runs.data !== undefined && !rows.length}>
        <div className="table-scroll"><table className="data-table">
          <thead><tr><th>Run</th><th>Kind</th><th>Result</th><th>Citations</th><th>Extraction</th><th>Grounded</th><th>Failed checks</th><th>Latency</th><th>Tokens</th><th>Cost</th><th>Scored</th></tr></thead>
          <tbody>{rows.map(r => { const u = record(r.usage); const failed = list(r.metrics).filter(m => m.status === 'failed' || m.status === 'error');
            return <tr key={text(r.id)}>
              <td>{r.run_kind === 'ask' ? <span title={text(r.question, '')}>{text(r.run_id)}</span> : <Link className="table-link" href={'/dashboard/workflow?run=' + encodeURIComponent(text(r.run_id))}>{text(r.run_id).slice(0, 8)}</Link>}</td>
              <td>{text(r.run_kind)}</td><td><Status value={r.status} /></td>
              {['citation_faithfulness', 'extraction_completeness', 'groundedness'].map(n => <td key={n}>{pct(metricOf(r, n)?.score)}</td>)}
              <td>{failed.length ? failed.map(m => <div key={text(m.name)} title={text(m.reason, '')}><Badge tone="red">{label(m.name)}</Badge></div>) : <span className="muted-note">none</span>}</td>
              <td>{number(u.latency_ms) !== undefined ? ((u.latency_ms as number) / 1000).toFixed(1) + ' s' : '—'}</td>
              <td>{(number(u.tokens_in) ?? 0) + (number(u.tokens_out) ?? 0)}</td><td>${(number(u.usd) ?? 0).toFixed(4)}</td><td>{dateText(r.created_at)}</td>
            </tr>; })}</tbody>
        </table></div>
      </ResourceState>
    </Panel>
    <SuitePanel />
  </>;
}
