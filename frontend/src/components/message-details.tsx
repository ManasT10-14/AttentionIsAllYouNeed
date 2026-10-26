'use client';
import Link from 'next/link';
import { ReportFindings } from './report-findings';
import { useState } from 'react';
import { useResource } from '@/lib/use-resource';
import { list, number, query, record, text, type ApiRecord } from '@/lib/api';
import { availableMessageResult, relatedMessageFindings } from '@/lib/message-context';
import { CitationChip, Citations, FieldValue, Status } from './api-ui';
function ResultValue({ value }: { value: unknown }) {
 const item = record(value);
 if (Array.isArray(value) && value.length && value.every(v => record(v).claim)) return <ReportFindings findings={list(value)} />;
 if (item.contract_id && item.clause_number) return <div><CitationChip value={item} />{item.quote ? <blockquote className="source-quote">{text(item.quote)}</blockquote> : null}</div>;
 if (Array.isArray(value)) return <div className="agent-result-items">{value.map((v, i) => <article key={i}><ResultValue value={v} /></article>)}</div>;
 if (value && typeof value === 'object') return <dl className="record-fields">{Object.entries(item).filter(([key, v]) => !['id', 'run_id', 'link'].includes(key) && v !== null && v !== undefined).map(([key, v]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd><ResultValue value={v} /></dd></div>)}</dl>;
 return <FieldValue value={value} />;
}
export function MessageDetails({ message, context = {} }: { message: ApiRecord; context?: ApiRecord }) {
 const [expanded, setExpanded] = useState(false);
 const payload = record(message.payload);
 const saved = record(payload.contribution);
 const loaded = useResource(expanded && !Object.keys(saved).length && message.id ? '/api/agent-messages/' + encodeURIComponent(text(message.id)) + '/result' : null);
 const needsReport = expanded && message.sender === 'synth' && !Object.keys(saved).length && !list(record(loaded.data).sections).length && !loaded.loading;
 const historical = useResource(needsReport && message.run_id ? '/api/reports/runs/' + encodeURIComponent(text(message.run_id)) : null);
 const currentReport = useResource(needsReport && !message.run_id ? (message.contract_id ? query('/api/reports/contract', {contract_id: text(message.contract_id)}) : '/api/reports/company') : null);
 const baseLocal = availableMessageResult(message, context);
 const report = record(record(historical.data).report);
 const fallbackReport = Object.keys(report).length ? report : record(currentReport.data);
 const reportResult = availableMessageResult({...message, payload: {result_snapshot: fallbackReport}}, context);
 const local = list(baseLocal.sections).length ? baseLocal : Object.keys(fallbackReport).length ? {...reportResult,
  source: Object.keys(report).length ? 'run_snapshot' : 'available_records',
  notice: Object.keys(report).length ? 'Saved final report for this run; it may include results produced after this handoff.' : 'Latest saved report. This reflects current records and is not a snapshot of this historical message.'} : baseLocal;
 const remote = record(loaded.data);
 const result = Object.keys(saved).length ? saved : list(remote.sections).length ? remote : local;
 const sections = list(result.sections);
 const related = relatedMessageFindings(message, context); const tools = list(message.tool_calls);
 const hasExtra = Object.keys(payload).length > 0 || related.requested.length > 0 || tools.length > 0;
 return <details className="message-context" onToggle={e => setExpanded(e.currentTarget.open)}><summary>More context{hasExtra ? ' · evidence & recorded details' : ''}</summary><div className="message-context-body">
 <section><h4>What this agent contributed</h4><p className="message-context-note">{result.source === 'message_time_snapshot' ? 'Saved with this handoff. Later runs do not change this snapshot.' : text(result.notice, 'Saved results and evidence.')}</p>
 {loaded.loading && <p>Loading recorded results…</p>}{loaded.error && !sections.length && !historical.loading && !currentReport.loading && <div className="message-context-note"><p>The server could not load additional results for this message.</p><button className="text-link" onClick={loaded.reload}>Retry loading results</button><details><summary>Connection details</summary><p>{loaded.error}</p><p>If this says Not Found, restart the backend to load the message-results endpoint.</p></details></div>}
 {sections.map((section, i) => <details className="agent-result-section" key={i} open={i === 0}><summary>{text(section.title)}{Array.isArray(section.value) ? ` (${section.value.length})` : ''}</summary><ResultValue value={section.value} /></details>)}
 {message.sender === 'synth' && <p><Link className="text-link" href={query('/dashboard/reports', { run: text(message.run_id, '') || undefined })}>Open this run’s final report</Link>{message.contract_id ? <> · <Link className="text-link" href={query('/dashboard/reports', { contract: text(message.contract_id) })}>Latest contract report</Link></> : <> · <Link className="text-link" href="/dashboard/reports?tab=contracts&contract=company">Latest company report</Link></>}</p>}
 {!sections.length && !loaded.loading && !historical.loading && !currentReport.loading && !loaded.error && <p className="message-context-note">No detailed result snapshot was saved for this message. See the recorded evidence below.</p>}
 </section>
 <details><summary>Technical details</summary>
 <dl className="message-routing"><div><dt>From</dt><dd>{text(message.sender)}</dd></div><div><dt>To</dt><dd>{text(message.receiver, 'Not recorded')}</dd></div><div><dt>Message type</dt><dd>{text(message.kind)}</dd></div>{message.run_id ? <div><dt>Run</dt><dd><code>{text(message.run_id)}</code></dd></div> : null}</dl>
 {Object.keys(payload).length > 0 && <section><h4>Recorded payload</h4><FieldValue value={Object.fromEntries(Object.entries(payload).filter(([key]) => !["contribution", "result_snapshot"].includes(key)))} /></section>}
 </details>
 {related.found.length > 0 && <section><h4>Related stored findings</h4><p className="message-context-note">These are the currently available finding records referenced by this message.</p>{related.found.map(f => <article key={text(f.id)}><header><strong>{text(f.claim ?? f.title)}</strong><Status value={f.severity} severity /><Status value={f.status} /></header>{f.attack_path ? <p>{text(f.attack_path)}</p> : null}{number(f.likelihood) !== undefined && <small>Estimated likelihood: {Math.round(number(f.likelihood)! * 100)}%</small>}<Citations values={f.citations} /><Link className="text-link" href={query('/dashboard/agent-review', { run: text(message.run_id, '') || undefined, finding: text(f.id) })}>Open finding and decisions</Link></article>)}</section>}
 {related.missing.length > 0 && <p className="message-context-note">Referenced finding records were not returned for: {related.missing.join(', ')}. Their IDs remain in the message history.</p>}
 {tools.length > 0 && <section><h4>Tools in this recorded interval</h4>{tools.map((tool, i) => <article key={i}><header><code>{text(tool.tool)}</code><Status value={tool.blocked ? 'blocked' : tool.ok === false ? 'failed' : 'done'} /><small>{text(tool.ms)}ms</small></header>{tool.summary ? <p>{text(tool.summary)}</p> : null}</article>)}</section>}
 {!hasExtra && !sections.length && !loaded.error && <p className="message-context-note">Only a summary was stored for this handoff. No additional explanation or payload was stored in the original handoff.</p>}
 {message.contract_id && message.contract_id !== 'cross' ? <Link className="text-link" href={query('/dashboard/contracts', { contract: text(message.contract_id) })}>View contract extraction and clause evidence</Link> : null}
 </div></details>;
}
