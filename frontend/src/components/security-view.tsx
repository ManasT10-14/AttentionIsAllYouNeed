'use client';
import { useRef, useState } from 'react';
import Link from 'next/link';
import { Check, X } from 'lucide-react';
import { useResource } from '@/lib/use-resource';
import { dateText, list, number, query, record, text } from '@/lib/api';
import { useWorkspace } from './providers';
import { Badge, Button, PageTitle, Panel, PanelTitle } from './ui';
import { MutationFeedback, ResourceState, Status, useMutation } from './api-ui';
import { securityReviewFeedback, securityReviewRequest } from '@/lib/security-review';

const SEVERITY_TONE: Record<string, string> = { critical: 'red', high: 'red', medium: 'amber', low: 'green', info: 'neutral' };

export function SecurityView() {
  const { canAdmin, demo } = useWorkspace();
  const [severity, setSeverity] = useState('');
  const [source, setSource] = useState('');
  const summary = useResource('/api/security/summary');
  const events = useResource(query('/api/security/events', { severity, source }));
  const held = useResource('/api/security/events?status=quarantined');
  const tools = useResource('/api/tools');
  const coverage = useResource('/api/security/status');
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [previewId, setPreviewId] = useState('');
  const preview = useResource(canAdmin && previewId ? '/api/security/events/' + encodeURIComponent(previewId) + '/evidence' : null);
  const [receipt, setReceipt] = useState<ReturnType<typeof securityReviewFeedback> | null>(null);
  const submitting = useRef(false);
  const m = useMutation();
  const s = record(summary.data);
  const bySev = record(s.by_severity);
  const rows = list(events.data);
  const quarantined = list(s.quarantined_events);
  const heldEvents = list(held.data);
  const toolRows = list(tools.data);
  const agents = [...new Set(toolRows.flatMap(t => Array.isArray(t.allowed_agents) ? t.allowed_agents.map(String) : []))].sort();
  const review = async (id: string, decision: string, revision = 0) => {
    if (submitting.current || !reasons[id]?.trim()) return;
    submitting.current = true; setReceipt(null);
    try {
      const result = await m.run('/api/security/events/' + encodeURIComponent(id), securityReviewRequest(decision, reasons[id], revision));
      if (result) setReceipt(securityReviewFeedback(result));
    } finally { submitting.current = false; }
  };
  const reasonField = (id: string) => <label>Review reason (required)<textarea maxLength={2000} value={reasons[id] ?? ''} disabled={m.pending || demo} onChange={e => setReasons(previous => ({ ...previous, [id]: e.target.value }))} placeholder="Explain the evidence supporting this decision" /></label>;
  const c = record(coverage.data);
  const evidence = record(record(preview.data).evidence);
  const original = record(evidence.source_event);
  return <>
    <PageTitle eyebrow="SECURITY" title="Inspect guard decisions and held events." description="Review recorded detections, quarantine, tool permissions and the scope of the active runtime controls." />
    <MutationFeedback mutation={{ ...m, success: '' }} />
    {receipt && <p role={receipt.error ? 'alert' : 'status'} className={receipt.error ? 'form-error' : 'mutation-success'}>{receipt.message} {receipt.runId && <Link href={'/dashboard/workflow?run=' + encodeURIComponent(receipt.runId)}>Open processing run</Link>}</p>}
    <Panel>
      <PanelTitle title="Runtime control coverage" description="Configuration and recorded decisions describe the active controls. They do not establish that every attack is prevented." />
      <ResourceState resource={coverage}>
        <div className="button-row"><Badge tone={c.guard_enabled ? 'green' : 'amber'}>{c.guard_enabled ? 'Guard loaded' : 'Guard not reported'}</Badge><Badge>{text(c.policy_version, 'Policy unavailable')}</Badge><Badge>Classifier: {text(record(c.classifier).status, 'unavailable')}</Badge><Badge>Audit sink: {text(record(c.audit_sink).status, 'unavailable')}</Badge></div>
        <p className="muted-note">Last recorded decision: {dateText(c.last_decision_at)} · Trace privacy: {text(c.trace_privacy_mode, 'unavailable')}</p>
        <ul>{list(c.protected_surfaces).map(surface => <li key={text(surface.name)}><strong>{text(surface.name).replaceAll('_', ' ')}</strong>: {text(surface.detail, text(surface.status))}</li>)}</ul>
        {Array.isArray(c.limitations) && c.limitations.map((limitation, i) => <p className="muted-note" key={i}>{String(limitation)}</p>)}
      </ResourceState>
    </Panel>
    <ResourceState resource={summary}>
      <div className="stats-grid">
        <Panel className="stat-card"><div className="stat-heading"><span>DETECTIONS</span><Badge tone={s.guard_enabled ? 'green' : 'amber'}>{s.guard_enabled ? 'Guard on' : 'Guard off'}</Badge></div><strong className="stat-value">{text(s.total, '0')}</strong><p>{text(s.open, '0')} open for review</p></Panel>
        <Panel className="stat-card"><div className="stat-heading"><span>HIGH / CRITICAL</span></div><strong className="stat-value">{(number(bySev.high) ?? 0) + (number(bySev.critical) ?? 0)}</strong><p>{number(bySev.medium) ?? 0} medium · {number(bySev.low) ?? 0} low</p></Panel>
        <Panel className="stat-card"><div className="stat-heading"><span>HELD / REVIEW EVENTS</span></div><strong className="stat-value">{quarantined.length}</strong><p>Email and scheduled events awaiting a decision or recovery</p></Panel>
        <Panel className="stat-card"><div className="stat-heading"><span>BLOCKED TOOL CALLS</span></div><strong className="stat-value">{list(s.blocked_tool_calls).length}</strong><p>Latest 50 from the audit log</p></Panel>
      </div>
      <Panel>
        <PanelTitle title="Quarantine" description="Held input stops before parsing, model fallback, rejection reply, clock movement and event processing." />
        {quarantined.length ? <div className="live-alert-list">{quarantined.map(ev => {
          const hits = [...heldEvents, ...rows].filter((e, i, all) => e.event_id === ev.id && all.findIndex(other => other.id === e.id) === i);
          const sid = text(ev.security_event_id, text(hits[0]?.id, ''));
          const revision = number(ev.review_revision) ?? number(hits[0]?.review_revision) ?? 0;
          const canReview = ev.status === 'quarantined' && !['release_pending', 'release_failed'].includes(text(ev.review_status, ''));
          return <article key={text(ev.id)}>
            <header><strong>{text(ev.subject, 'No subject')}</strong><Status value={ev.status ?? 'quarantined'} /></header>
            <p>{text(ev.sender, 'manual')} · {text(ev.event_type, '')} · {dateText(ev.occurred_at)}</p>
            {ev.reject_reason ? <p>{text(ev.reject_reason)}</p> : null}
            {hits.map(h => <p key={text(h.id)}><Badge tone={SEVERITY_TONE[text(h.severity, '')] ?? 'neutral'}>{text(h.severity)}</Badge> {text(h.rule).replaceAll('_', ' ')}: <q>{text(h.snippet, '')}</q></p>)}
            {canAdmin && sid && <>
              <Button variant="ghost" disabled={demo} onClick={() => setPreviewId(sid)}>Inspect redacted evidence</Button>
              {canReview ? <>
                {reasonField(sid)}
                <p className="muted-note">Release validates the original source, may advance the simulated clock, and starts one processing run. Confirm rejects the event. Dismiss closes the detection and leaves the event held.</p>
                <div className="button-row">
                  <Button variant="secondary" disabled={m.pending || demo || !reasons[sid]?.trim()} onClick={() => void review(sid, 'release', revision)}><Check size={14} />Release &amp; process</Button>
                  <Button variant="secondary" disabled={m.pending || demo || !reasons[sid]?.trim()} onClick={() => void review(sid, 'confirm', revision)}><X size={14} />Confirm &amp; reject</Button>
                  <Button variant="ghost" disabled={m.pending || demo || !reasons[sid]?.trim()} onClick={() => void review(sid, 'dismiss', revision)}>Dismiss detection only</Button>
                </div>
              </> : <p role="status">{ev.review_release_status === 'release_failed' ? 'Release failed. Manual recovery is required; automatic replay is disabled.' : 'Release is claimed. Refresh to inspect its result.'}</p>}
            </>}
          </article>; })}</div> : <p className="muted-note">Nothing in quarantine.</p>}
      </Panel>
    </ResourceState>
    {canAdmin && previewId && <Panel>
      <PanelTitle title="Redacted source evidence" description="Canonical source is retained privately. This preview applies the privacy policy."><Button variant="ghost" onClick={() => setPreviewId('')}>Close</Button></PanelTitle>
      <ResourceState resource={preview}>
        <p><strong>{text(evidence.subject, text(original.subject, 'Source event'))}</strong></p>
        <pre className="muted-note" style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{text(evidence.body, text(original.raw, text(original.description, 'Original source unavailable for this historical incident.')))}</pre>
      </ResourceState>
    </Panel>}
    <Panel>
      <PanelTitle title="Detection log" description="Every guard decision: what was found, where, and what was done">
        <div className="filter-bar">
          <label>Severity<select value={severity} onChange={e => setSeverity(e.target.value)}><option value="">All</option>{['critical', 'high', 'medium', 'low'].map(v => <option key={v}>{v}</option>)}</select></label>
          <label>Source<select value={source} onChange={e => setSource(e.target.value)}><option value="">All</option>{['ingest', 'company_context', 'email', 'scheduled_event', 'llm_input', 'tool_result', 'tool_call'].map(v => <option key={v}>{v}</option>)}</select></label>
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
            {canAdmin && <td>{e.status === 'open' && <>{reasonField(text(e.id))}<Button variant="ghost" disabled={m.pending || demo || !reasons[text(e.id)]?.trim()} onClick={() => void review(text(e.id), 'dismiss', number(e.review_revision) ?? 0)}>Dismiss detection</Button></>}</td>}
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
