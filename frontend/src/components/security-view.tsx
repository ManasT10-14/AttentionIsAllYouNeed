'use client';
import { useState } from 'react';
import { Check, X } from 'lucide-react';
import { useResource } from '@/lib/use-resource';
import { dateText, list, number, query, record, text } from '@/lib/api';
import { useWorkspace } from './providers';
import { Badge, Button, PageTitle, Panel, PanelTitle } from './ui';
import { MutationFeedback, ResourceState, Status, useMutation } from './api-ui';

const SEVERITY_TONE: Record<string, string> = { critical: 'red', high: 'red', medium: 'amber', low: 'green', info: 'neutral' };

export function SecurityView() {
  const { canAdmin, demo } = useWorkspace();
  const [severity, setSeverity] = useState('');
  const [source, setSource] = useState('');
  const summary = useResource('/api/security/summary');
  const events = useResource(query('/api/security/events', { severity, source }));
  const held = useResource('/api/security/events?status=quarantined');
  const tools = useResource('/api/tools');
  const m = useMutation();
  const s = record(summary.data);
  const bySev = record(s.by_severity);
  const rows = list(events.data);
  const quarantined = list(s.quarantined_events);
  const heldEvents = list(held.data);
  const toolRows = list(tools.data);
  const agents = [...new Set(toolRows.flatMap(t => Array.isArray(t.allowed_agents) ? t.allowed_agents.map(String) : []))].sort();
  const review = (id: string, decision: string) => void m.run('/api/security/events/' + encodeURIComponent(id), { decision });
  return <>
    <PageTitle eyebrow="SECURITY" title="Guard every input and action." description="Prompt-injection detection on uploads, emails and tool results, secret redaction, tool policy and tenant isolation — enforced at runtime." />
    <MutationFeedback mutation={m} />
    <ResourceState resource={summary}>
      <div className="stats-grid">
        <Panel className="stat-card"><div className="stat-heading"><span>DETECTIONS</span><Badge tone={s.guard_enabled ? 'green' : 'amber'}>{s.guard_enabled ? 'Guard on' : 'Guard off'}</Badge></div><strong className="stat-value">{text(s.total, '0')}</strong><p>{text(s.open, '0')} open for review</p></Panel>
        <Panel className="stat-card"><div className="stat-heading"><span>HIGH / CRITICAL</span></div><strong className="stat-value">{(number(bySev.high) ?? 0) + (number(bySev.critical) ?? 0)}</strong><p>{number(bySev.medium) ?? 0} medium · {number(bySev.low) ?? 0} low</p></Panel>
        <Panel className="stat-card"><div className="stat-heading"><span>QUARANTINED EMAILS</span></div><strong className="stat-value">{quarantined.length}</strong><p>Held until an admin releases or confirms them</p></Panel>
        <Panel className="stat-card"><div className="stat-heading"><span>BLOCKED TOOL CALLS</span></div><strong className="stat-value">{list(s.blocked_tool_calls).length}</strong><p>Latest 50 from the audit log</p></Panel>
      </div>
      <Panel>
        <PanelTitle title="Quarantine" description="Emails with injected instructions are parsed but never run until reviewed" />
        {quarantined.length ? <div className="live-alert-list">{quarantined.map(ev => {
          const hits = heldEvents.filter(e => e.event_id === ev.id);
          return <article key={text(ev.id)}>
            <header><strong>{text(ev.subject, 'No subject')}</strong><Status value="quarantined" /></header>
            <p>{text(ev.sender, 'manual')} · {text(ev.event_type, '')} · {dateText(ev.occurred_at)}</p>
            {hits.map(h => <p key={text(h.id)}><Badge tone={SEVERITY_TONE[text(h.severity, '')] ?? 'neutral'}>{text(h.severity)}</Badge> {text(h.rule).replaceAll('_', ' ')}: <q>{text(h.snippet, '')}</q></p>)}
            {canAdmin && hits[0] && <div className="button-row">
              <Button variant="secondary" disabled={m.pending || demo} onClick={() => review(text(hits[0].id), 'release')}><Check size={14} />Release &amp; process</Button>
              <Button variant="secondary" disabled={m.pending || demo} onClick={() => review(text(hits[0].id), 'confirm')}><X size={14} />Confirm injection</Button>
            </div>}
          </article>; })}</div> : <p className="muted-note">Nothing in quarantine.</p>}
      </Panel>
    </ResourceState>
    <Panel>
      <PanelTitle title="Detection log" description="Every guard decision: what was found, where, and what was done">
        <div className="filter-bar">
          <label>Severity<select value={severity} onChange={e => setSeverity(e.target.value)}><option value="">All</option>{['critical', 'high', 'medium', 'low'].map(v => <option key={v}>{v}</option>)}</select></label>
          <label>Source<select value={source} onChange={e => setSource(e.target.value)}><option value="">All</option>{['ingest', 'company_context', 'email', 'llm_input', 'tool_result', 'tool_call'].map(v => <option key={v}>{v}</option>)}</select></label>
        </div>
      </PanelTitle>
      <ResourceState resource={events} empty={events.data !== undefined && !rows.length}>
        <div className="table-scroll"><table className="data-table">
          <thead><tr><th>Severity</th><th>Kind</th><th>Source</th><th>Rule</th><th>Snippet</th><th>Action</th><th>Status</th><th>Where</th><th>When</th>{canAdmin && <th />}</tr></thead>
          <tbody>{rows.map(e => <tr key={text(e.id)}>
            <td><Badge tone={SEVERITY_TONE[text(e.severity, '')] ?? 'neutral'}>{text(e.severity)}</Badge></td>
            <td>{text(e.kind).replaceAll('_', ' ')}</td><td>{text(e.source).replaceAll('_', ' ')}</td><td>{text(e.rule).replaceAll('_', ' ')}</td>
            <td><small>{text(e.snippet, '')}</small></td><td><Status value={e.action} /></td><td><Status value={e.status} /></td>
            <td><small>{[e.contract_id, e.filename, e.event_id, e.agent, e.tool].filter(Boolean).map(String).join(' · ') || '—'}</small></td>
            <td>{dateText(e.created_at)}</td>
            {canAdmin && <td>{e.status === 'open' && <Button variant="ghost" disabled={m.pending || demo} onClick={() => review(text(e.id), 'dismiss')}>Dismiss</Button>}</td>}
          </tr>)}</tbody>
        </table></div>
      </ResourceState>
    </Panel>
    <Panel>
      <PanelTitle title="Blocked tool calls" description="Denied by the allowlist, the approval gate or the runtime guard" />
      <ResourceState resource={summary} empty={summary.data !== undefined && !list(s.blocked_tool_calls).length}>
        <div className="table-scroll"><table className="data-table">
          <thead><tr><th>Agent</th><th>Tool</th><th>Scope</th><th>Reason</th><th>Run</th><th>When</th></tr></thead>
          <tbody>{list(s.blocked_tool_calls).map((t, i) => <tr key={i}><td>{text(t.agent)}</td><td>{text(t.tool)}</td><td>{text(t.scope)}</td><td><small>{text(t.summary, '')}</small></td><td><small>{text(t.run_id, '—').slice(0, 8)}</small></td><td>{dateText(t.ts)}</td></tr>)}</tbody>
        </table></div>
      </ResourceState>
    </Panel>
    <Panel>
      <PanelTitle title="Tool permission matrix" description="Which agent may call which tool, from the live tool registry" />
      <ResourceState resource={tools} empty={tools.data !== undefined && !toolRows.length}>
        <div className="table-scroll"><table className="data-table">
          <thead><tr><th>Tool</th><th>Scope</th><th>Policy</th>{agents.map(a => <th key={a}>{a}</th>)}</tr></thead>
          <tbody>{toolRows.map(t => { const allowed = Array.isArray(t.allowed_agents) ? t.allowed_agents.map(String) : [];
            return <tr key={text(t.name)}><td><strong>{text(t.name)}</strong></td><td>{text(t.scope).replaceAll('_', ' ')}</td>
              <td><div className="button-row">{t.requires_approval === true && <Badge tone="amber">approval</Badge>}{t.side_effect === true && <Badge tone="red">side effect</Badge>}{t.pii === true && <Badge tone="purple">PII</Badge>}</div></td>
              {agents.map(a => <td key={a} aria-label={allowed.includes(a) ? 'allowed' : 'denied'}>{allowed.includes(a) ? <Check size={14} /> : <span className="muted-note">·</span>}</td>)}</tr>; })}</tbody>
        </table></div>
      </ResourceState>
    </Panel>
  </>;
}
