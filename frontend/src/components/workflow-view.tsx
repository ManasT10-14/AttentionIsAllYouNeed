'use client';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { dateText, list, number, query, record, text } from '@/lib/api';
import { useResource } from '@/lib/use-resource';
import { Badge, PageTitle, Panel, PanelTitle } from './ui';
import { Citations, DownloadLink, ResourceState, SourceBadge, Status, TraceLink } from './api-ui';

const kindLabel: Record<string, string> = { analysis: 'Analysis', event: 'Event', update: 'Amendment re-run', report: 'Report refresh', whatif: 'What-if' };
const clock = (v: unknown) => text(v, '').slice(11, 19);

export function WorkflowView() {
 const router = useRouter(); const params = useSearchParams();
 const contract = params.get('contract') ?? ''; const event = params.get('event') ?? ''; const runParam = params.get('run') ?? '';
 const runs = useResource(query('/api/runs', { contract_id: contract, event_id: event }));
 const rows = list(runs.data); const runId = runParam || text(rows[0]?.id, '');
 const wf = useResource(runId ? '/api/workflow/' + encodeURIComponent(runId) : null);
 const w = record(wf.data); const run = record(w.run); const tl = record(w.timeline); const remarks = record(w.remarks); const outputs = record(w.outputs);
 const pick = (id: string) => router.push(query('/dashboard/workflow', { run: id, contract, event }));
 const scopeLabel = event ? 'event ' + event : contract ? 'contract ' + contract : 'this workspace';
 return <><PageTitle eyebrow="WORKFLOW EXECUTION" title="What the agents did." description={'Runs that touched ' + scopeLabel + ': plan, agent timeline, debate, outputs and final remarks.'}>{(contract || event) && <Link className="button button-secondary" href="/dashboard/workflow">Show all runs</Link>}</PageTitle>
 <div className="inbox-layout"><div>
 <Panel><PanelTitle title="Runs" description="Newest first. Pick one to inspect." /><ResourceState resource={runs} empty={runs.data !== undefined && !rows.length}><div className="inbox-event-list">{rows.map(r => <button key={text(r.id)} className="inbox-event-row" aria-current={text(r.id) === runId} onClick={() => pick(text(r.id))}><span className="inbox-event-summary"><strong>{kindLabel[text(r.kind, '')] ?? text(r.kind)}{text(r.id) === runId ? ' (selected)' : ''}</strong><small>{dateText(r.started_at)} · {text(r.id).slice(0, 8)}</small></span><Status value={r.status} /></button>)}</div></ResourceState></Panel>
 </div><div>
 {!runId ? null : <ResourceState resource={wf}>{wf.data !== undefined && <>
 <Panel><PanelTitle title={(kindLabel[text(run.kind, '')] ?? 'Run') + ' · ' + text(run.id).slice(0, 8)} description={'Started ' + dateText(run.started_at) + (run.finished_at ? ' · finished ' + dateText(run.finished_at) : '')}><Status value={run.status} /></PanelTitle>
  <div className="button-row"><TraceLink value={w.trace_url} />{!w.trace_url && <small className="muted-note">No LangSmith trace link for this run.</small>}</div>
  {tl.running ? <p role="status" className="muted-note"><i className="status-dot" /> Running now: <strong>{text(tl.current_agent, 'odin')}</strong></p> : null}</Panel>
 <Panel><PanelTitle title="Work plan" description="Workstreams and their status"><SourceBadge value="analysis" /></PanelTitle>{list(w.workstreams).length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Workstream</th><th>Status</th><th>Evidence</th><th>Reason</th></tr></thead><tbody>{list(w.workstreams).map(s => <tr key={text(s.id)}><td>{text(s.contract_id)}</td><td><Status value={s.status} /></td><td>{number(s.evidence_score) === undefined ? '—' : Math.round(number(s.evidence_score)! * 100) + '%'}</td><td>{text(s.reason, '')}</td></tr>)}</tbody></table></div> : <p className="muted-note">This run has no workstreams (event runs follow a fixed pipeline).</p>}</Panel>
 <Panel><PanelTitle title="Agent timeline" description={text(tl.tool_call_count, '0') + ' tool calls · updates live'} />
  <div className="table-scroll"><table className="data-table"><thead><tr><th>Agent</th><th>Step</th><th>Time</th><th>Duration</th><th>Tools</th></tr></thead><tbody>{list(tl.steps).map(s => <tr key={text(s.id)}><td><strong>{text(s.sender)}</strong> → {text(s.receiver)}<small>{text(s.kind)}</small></td><td>{text(s.summary)}</td><td>{clock(s.started_at)}–{clock(s.ended_at)}</td><td>{text(s.duration_s)}s</td><td>{list(s.tool_calls).length ? <details><summary>{list(s.tool_calls).length} call(s)</summary>{list(s.tool_calls).map((c, i) => <div key={i}><code>{text(c.tool)}</code> {c.ok === false || c.blocked ? '(failed) ' : ''}{text(c.ms)}ms</div>)}</details> : '—'}</td></tr>)}</tbody></table></div>
  {!list(tl.steps).length && <p className="muted-note">No agent messages yet.</p>}
  <h3 className="detail-section-title">Per-agent usage</h3><div className="table-scroll"><table className="data-table"><thead><tr><th>Agent</th><th>LLM calls</th><th>Tokens</th><th>Cost (USD)</th><th>LLM time</th></tr></thead><tbody>{Object.entries(record(tl.agents)).map(([a, v]) => <tr key={a}><td>{a}</td><td>{text(record(v).calls)}</td><td>{text(record(v).tokens)}</td><td>{number(record(v).usd)?.toFixed(4)}</td><td>{Math.round((number(record(v).latency_ms) ?? 0) / 1000)}s</td></tr>)}</tbody></table></div></Panel>
 <Panel><PanelTitle title="Debate" description="Loki finding, Heimdall verification, Tyr ruling" />{list(w.debate).map((d, i) => { const f = record(d.finding); const ru = record(d.ruling); return <article className="version-diff" key={i}><div><Badge tone="amber">Loki</Badge> <strong>{text(f.claim)}</strong> <Status value={f.severity} severity /></div><Citations values={f.citations} />{list(d.verifications).map((v, j) => <p key={j}><Badge tone="purple">Heimdall</Badge> <Status value={v.verdict} /> {text(v.rationale)}</p>)}{d.ruling ? <p><Badge tone="green">Tyr</Badge> winner {text(ru.winner)}, severity {text(ru.final_severity)}/5. {text(ru.rationale)}</p> : <p className="muted-note">No ruling (not disputed or not reached).</p>}</article>; })}{!list(w.debate).length && <p className="muted-note">This run produced no findings to debate.</p>}</Panel>
 <Panel><PanelTitle title="Outputs created" description="Findings, violations, alerts and actions from this run" />{['finding', 'violation', 'alert', 'action'].map(k => <div key={k}><h3 className="detail-section-title">{k}s ({list(outputs[k]).length})</h3>{list(outputs[k]).slice(0, 25).map(o => <p key={text(o.id)}><Status value={o.status} /> {text(o.claim ?? o.explanation ?? o.title ?? o.subject)} <small>{text(o.contract_id, '')}</small></p>)}</div>)}</Panel>
 <Panel><PanelTitle title="Final remarks" description="Gate decision"><Badge tone={remarks.complete ? 'green' : 'amber'}>{remarks.complete ? 'COMPLETE' : text(remarks.decision, '').toUpperCase()}</Badge></PanelTitle>{remarks.error ? <p className="form-error">{text(remarks.error)}</p> : null}{list(remarks.gaps).length ? <ul>{list(remarks.gaps).map((g, i) => <li key={i}><strong>{text(g.contract_id)}</strong> <Status value={g.status} /> {text(g.reason, '')}</li>)}</ul> : <p className="muted-note">No gaps reported.</p>}
  <h3 className="detail-section-title">Reports</h3><div className="button-row">{list(w.reports).map(r => <span key={text(r.path)}><Link className="button button-secondary" href={r.kind === 'event' ? query('/dashboard/reports', { event: text(w.event_id) }) : query('/dashboard/reports', { run: runId })}>{text(r.title)}</Link> <DownloadLink path={text(r.path) + '?format=pdf'}>PDF</DownloadLink></span>)}{!list(w.reports).length && <p className="muted-note">No report for this run.</p>}</div></Panel>
 </>}</ResourceState>}
 </div></div></>;
}
