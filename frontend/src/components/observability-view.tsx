'use client';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Activity, Coins, Gauge, Hash, ShieldCheck, ShieldOff, Timer, Workflow } from 'lucide-react';
import { useResource } from '@/lib/use-resource';
import { runTitle } from '@/lib/run-presentation';
import { dateTimeText, list, number, query, record, text, type ApiRecord } from '@/lib/api';
import { PageTitle, Panel, PanelTitle } from './ui';
import { FieldValue, ResourceState, SourceBadge, Status, TraceLink } from './api-ui';
import '@/app/insights-views.css';

const usd = (v: number) => v === 0 ? '$0' : v < 0.01 ? '<$0.01' : '$' + v.toFixed(v < 1 ? 3 : 2);
const ms = (v: number) => v >= 60000 ? (v / 60000).toFixed(1) + ' min' : v >= 1000 ? (v / 1000).toFixed(1) + ' s' : Math.round(v) + ' ms';
const tok = (v: number) => v >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? (v / 1e3).toFixed(1) + 'k' : String(v);
const duration = (r: ApiRecord) => { const a = Date.parse(text(r.started_at, '')), b = Date.parse(text(r.finished_at, '')); return Number.isNaN(a) || Number.isNaN(b) ? undefined : b - a; };
function p95(values: number[]) { if (!values.length) return 0; const v = [...values].sort((a, b) => a - b); return v[Math.min(v.length - 1, Math.ceil(v.length * 0.95) - 1)]; }
function Bar({ value, max }: { value: number; max: number }) { return <span className="ob-bar" aria-hidden><i style={{ width: (max > 0 ? Math.max(2, value / max * 100) : 0) + '%' }} /></span>; }
function Kpi({ icon: Icon, label, value, hint, tone }: { icon: typeof Activity; label: string; value: string; hint?: string; tone?: string }) { return <div className={'ob-kpi' + (tone ? ' ' + tone : '')}><span><Icon size={14} aria-hidden />{label}</span><strong>{value}</strong>{hint && <small>{hint}</small>}</div>; }

export function ObservabilityView() {
  const contracts = useResource('/api/contracts'); const events = useResource('/api/events');
  const r = useResource('/api/observability'); const tools = useResource('/api/tools'); const calibration = useResource('/api/insights/calibration');
  const [selected, setSelected] = useState(''); const [step, setStep] = useState(0); const [agent, setAgent] = useState(''); const [tool, setTool] = useState(''); const [blocked, setBlocked] = useState(false);
  const run = useResource(selected ? '/api/runs/' + encodeURIComponent(selected) : null); const data = record(run.data); const messages = list(data.messages); const calls = list(data.tool_calls).filter(c => (!agent || c.agent === agent) && (!tool || c.tool === tool) && (!blocked || c.blocked === true));
  const observation = record(r.data); const runs = list(observation.runs); const buckets = list(record(calibration.data).buckets);
  const guard = record(observation.citation_guard); const providers = record(observation.providers); const limits = record(observation.limits);
  useEffect(() => setStep(0), [selected]);
  const stats = useMemo(() => {
    const per = new Map<string, { calls: number; tokens: number; usd: number; latency: number; perRun: number[]; providers: Map<string, number> }>();
    let usdTotal = 0, tokensIn = 0, tokensOut = 0, calls = 0, latency = 0, fallbacks = 0;
    for (const item of runs) {
      const b = record(item.budget); usdTotal += number(b.usd) ?? 0; tokensIn += number(b.tokens_in) ?? 0; tokensOut += number(b.tokens_out) ?? 0; fallbacks += number(b.fallbacks) ?? 0;
      for (const [name, raw] of Object.entries(record(b.per_agent))) {
        const v = record(raw); const e = per.get(name) ?? { calls: 0, tokens: 0, usd: 0, latency: 0, perRun: [] as number[], providers: new Map<string, number>() };
        const c = number(v.calls) ?? 0, l = number(v.latency_ms) ?? 0; e.calls += c; e.tokens += number(v.tokens) ?? 0; e.usd += number(v.usd) ?? 0; e.latency += l; if (c) e.perRun.push(l / c);
        for (const [p, n] of Object.entries(record(v.providers))) e.providers.set(p, (e.providers.get(p) ?? 0) + (number(n) ?? 0));
        per.set(name, e); calls += c; latency += l;
      }
    }
    const agents = [...per.entries()].map(([name, e]) => ({ name, ...e, avg: e.calls ? e.latency / e.calls : 0, p95: p95(e.perRun) })).sort((a, b) => b.usd - a.usd);
    return { agents, usdTotal, tokens: tokensIn + tokensOut, tokensIn, tokensOut, avg: calls ? latency / calls : 0, calls, fallbacks };
  }, [runs]);
  const ok = runs.filter(x => ['done', 'completed', 'success'].includes(text(x.status, ''))).length; const partial = runs.filter(x => x.status === 'partial').length; const failed = runs.filter(x => ['failed', 'error'].includes(text(x.status, ''))).length;
  const blockedCalls = number(observation.blocked_tool_calls) ?? 0; const usage = list(observation.tool_usage); const usageMax = Math.max(1, ...usage.map(u => number(u.calls) ?? 0));
  const maxUsd = Math.max(0, ...stats.agents.map(a => a.usd)), maxLat = Math.max(0, ...stats.agents.map(a => a.p95)), maxTok = Math.max(0, ...stats.agents.map(a => a.tokens));
  const stored = number(guard.stored_citations), unverified = number(guard.stored_unverified) ?? 0;
  const fallback = Array.isArray(providers.fallback) ? (providers.fallback as string[]).join(' → ') || 'none' : '–';
  return <><PageTitle eyebrow="OBSERVABILITY" title="See how the work gets done." description="What the agents ran, what it cost, how fast it was, and whether every claim stayed grounded in the contract." />
    <ResourceState resource={r}>
      <div className="ob-kpis">
        <Kpi icon={Activity} label="Runs" value={String(runs.length)} hint={`${ok} complete · ${partial} partial · ${failed} failed`} tone={failed ? 'bad' : undefined} />
        <Kpi icon={Coins} label="Total cost" value={usd(stats.usdTotal)} hint={runs.length ? usd(stats.usdTotal / runs.length) + ' per run' : undefined} />
        <Kpi icon={Hash} label="Tokens" value={tok(stats.tokens)} hint={`${tok(stats.tokensIn)} in · ${tok(stats.tokensOut)} out`} />
        <Kpi icon={Timer} label="Avg agent latency" value={stats.calls ? ms(stats.avg) : '–'} hint={`${stats.calls} agent calls`} />
        <Kpi icon={blockedCalls ? ShieldOff : ShieldCheck} label="Blocked tool calls" value={String(blockedCalls)} hint={blockedCalls ? 'Policy stopped these' : 'Nothing was blocked'} tone={blockedCalls ? 'bad' : 'good'} />
        <Kpi icon={Gauge} label="Citation guard" value={stored === undefined ? '–' : unverified ? `${unverified} unverified` : 'All verified'} hint={stored === undefined ? undefined : `${stored} stored citations` + (guard.blocked !== undefined ? ` · ${text(guard.blocked)} blocked this session` : '')} tone={unverified ? 'bad' : 'good'} />
      </div>
      <div className="ob-grid">
        <Panel className="ob-agents"><PanelTitle title="Agents" description={`Across the last ${runs.length} run${runs.length === 1 ? '' : 's'}${stats.fallbacks ? ` · ${stats.fallbacks} provider fallback${stats.fallbacks === 1 ? '' : 's'}` : ''}`} />
          {stats.agents.length ? <div className="table-scroll"><table className="data-table ob-table"><thead><tr><th>Agent</th><th className="num">Calls</th><th>Latency avg / p95</th><th>Tokens</th><th>Cost</th></tr></thead><tbody>{stats.agents.map(a => <tr key={a.name}><td><strong className="ob-agent">{a.name}</strong><small>{[...a.providers].map(([p, n]) => `${p} ×${n}`).join(', ')}</small></td><td className="num">{a.calls}</td><td><span className="ob-cell">{ms(a.avg)} / {ms(a.p95)}</span><Bar value={a.p95} max={maxLat} /></td><td><span className="ob-cell">{tok(a.tokens)}</span><Bar value={a.tokens} max={maxTok} /></td><td><span className="ob-cell">{usd(a.usd)}</span><Bar value={a.usd} max={maxUsd} /></td></tr>)}</tbody></table></div> : <p className="muted-note">No agent calls recorded yet.</p>}
          <p className="ob-foot">p95 is taken over each run&apos;s average call latency. Errors are tracked per run, not per agent.</p></Panel>
        <Panel className="ob-config"><PanelTitle title="Model and limits" description="Read-only configuration" />
          <dl className="ob-dl"><div><dt>Primary provider</dt><dd>{text(providers.provider, '–')}</dd></div><div><dt>Fallback chain</dt><dd>{fallback}</dd></div><div><dt>Temperature</dt><dd>{text(providers.temperature, '–')}</dd></div><div><dt>Retries</dt><dd>{text(providers.max_retries, '–')}</dd></div><div><dt>Budget per run</dt><dd>{limits.max_usd !== undefined ? '$' + text(limits.max_usd) : '–'}</dd></div><div><dt>Token cap</dt><dd>{limits.max_tokens !== undefined ? tok(Number(limits.max_tokens)) : '–'}</dd></div><div><dt>Agent call cap</dt><dd>{text(limits.max_agent_calls, '–')}</dd></div><div><dt>Confidence / evidence bar</dt><dd>{text(limits.confidence_threshold, '–')} / {text(limits.evidence_threshold, '–')}</dd></div></dl>
          <details><summary>All settings</summary><FieldValue value={{ providers, limits }} /></details></Panel>
      </div>
      <Panel className="ob-runs"><PanelTitle title="Recent runs" description="Open a run to see its workflow, replay its messages or follow the external trace" />
        {runs.length ? <ul className="ob-run-list">{runs.map(x => { const id = text(x.id); const d = duration(x); const b = record(x.budget); return <li key={id} className={selected === id ? 'on' : ''}>
          <div className="ob-run-main"><Status value={x.status} /><strong>{runTitle(x, list(contracts.data), list(events.data))}</strong><code className="run-id">{id.slice(0, 8)}</code><small>{dateTimeText(x.started_at)}{d !== undefined ? ' · ' + ms(d) : ''}</small>{text(x.error, '') && <small className="ob-err">{text(x.error)}</small>}</div>
          <div className="ob-run-meta"><span>{usd(number(b.usd) ?? 0)}</span><span>{tok((number(b.tokens_in) ?? 0) + (number(b.tokens_out) ?? 0))} tok</span><span>{text(b.agent_calls, '0')} agent calls</span><span>{text(b.tool_calls, '0')} tool calls</span></div>
          <div className="ob-run-actions"><Link className="text-link" href={query('/dashboard/workflow', { run: id })}><Workflow size={12} aria-hidden /> Workflow</Link><Link className="text-link" href={query('/dashboard/reports', { run: id })}>Report</Link><button className="text-link" onClick={() => setSelected(selected === id ? '' : id)}>{selected === id ? 'Hide replay' : 'Replay'}</button><TraceLink value={x.trace_url} />{!text(x.trace_url, '') && <small className="muted-note">No trace link</small>}</div></li>; })}</ul> : <p className="muted-note">No runs yet. Upload a contract or add an event to start one.</p>}</Panel>
    </ResourceState>
    {selected && <Panel><PanelTitle title={'Run replay · ' + selected.slice(0, 8)}><TraceLink value={data.trace_url} /></PanelTitle><ResourceState resource={run}><label className="input-label">Message {messages.length ? Math.min(step + 1, messages.length) : 0} of {messages.length}<input type="range" min="0" max={Math.max(0, messages.length - 1)} value={Math.min(step, Math.max(0, messages.length - 1))} onChange={e => setStep(Number(e.target.value))} disabled={!messages.length} /></label>{messages[step] ? <div className="replay-frame"><strong>{text(messages[step].sender)} → {text(messages[step].receiver)}</strong><Status value={messages[step].kind} /><p>{text(messages[step].summary)}</p><details><summary>Raw message</summary><FieldValue value={messages[step]} /></details></div> : <p>No messages supplied.</p>}
      <PanelTitle title="Tool audit log" /><div className="filter-bar"><input className="input" aria-label="Filter audit by agent" value={agent} onChange={e => setAgent(e.target.value)} placeholder="Agent" /><input className="input" aria-label="Filter audit by tool" value={tool} onChange={e => setTool(e.target.value)} placeholder="Tool" /><label className="checkbox-label"><input type="checkbox" checked={blocked} onChange={e => setBlocked(e.target.checked)} />Blocked only</label></div>
      {calls.length ? <div className="table-scroll"><table className="data-table"><thead><tr>{['agent', 'tool', 'scope', 'ok', 'blocked', 'ms', 'summary'].map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>{calls.map((call, i) => <tr key={i}>{['agent', 'tool', 'scope', 'ok', 'blocked', 'ms', 'summary'].map(c => <td key={c}><FieldValue value={call[c]} /></td>)}</tr>)}</tbody></table></div> : <p className="muted-note">No matching tool calls.</p>}</ResourceState></Panel>}
    <div className="ob-grid">
      <Panel><PanelTitle title="Tool usage" description="Calls by agent and tool" />{usage.length ? <table className="data-table ob-table"><thead><tr><th>Agent</th><th>Tool</th><th>Calls</th></tr></thead><tbody>{usage.map((u, i) => <tr key={i}><td>{text(u.agent)}</td><td><code>{text(u.tool)}</code></td><td><span className="ob-cell">{text(u.calls)}</span><Bar value={number(u.calls) ?? 0} max={usageMax} /></td></tr>)}</tbody></table> : <p className="muted-note">No tool calls recorded.</p>}</Panel>
      <Panel><PanelTitle title="Confidence calibration" description="How often claims at each confidence level were verified" /><ResourceState resource={calibration} empty={calibration.data !== undefined && !buckets.length}><div className="calibration-bars">{buckets.map((b, i) => <div key={i}><span>{text(b.confidence)}</span><progress max="1" value={typeof b.verified_rate === 'number' ? b.verified_rate : 0} /><b>{typeof b.verified_rate === 'number' ? Math.round(b.verified_rate * 100) + '%' : 'Not supplied'}</b><small>n = {text(b.n)}</small></div>)}</div></ResourceState></Panel>
    </div>
    <Panel><PanelTitle title="Tool registry" description="What each agent is allowed to call"><SourceBadge value="analysis" /></PanelTitle><ResourceState resource={tools}><div className="table-scroll"><table className="data-table ob-table"><thead><tr><th>Tool</th><th>Scope</th><th>Allowed agents</th><th>Guards</th></tr></thead><tbody>{list(tools.data).map(t => <tr key={text(t.name)}><td><code>{text(t.name)}</code><small>{text(t.description)}</small></td><td>{text(t.scope)}</td><td>{(Array.isArray(t.allowed_agents) ? t.allowed_agents as string[] : []).join(', ') || '–'}</td><td>{[t.side_effect === true && 'writes data', t.requires_approval === true && 'needs approval', t.pii === true && 'handles PII', t.llm_visible === false && 'hidden from LLM'].filter(Boolean).join(' · ') || 'read-only'}</td></tr>)}</tbody></table></div></ResourceState></Panel></>;
}
