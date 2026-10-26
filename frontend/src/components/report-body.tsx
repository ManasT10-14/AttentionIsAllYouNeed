'use client';
import Link from 'next/link';
import { reportReadiness } from '@/lib/report-readiness';
import type { ReactNode } from 'react';
import { dateText, formatMoney, list, number, query, record, text, type ApiRecord } from '@/lib/api';
import { activityTimeText } from '@/lib/activity-time';
import { useWorkspace } from './providers';
import { Citations, FieldValue, Status } from './api-ui';
import { ReportFindings } from './report-findings';

function Section({title, tone = 'blue', children}: {title: string; tone?: string; children: ReactNode}) {
 return <section className={'report-section report-tone-' + tone}><h3>{title}</h3>{children}</section>;
}
function Agreement({id}: {id: unknown}) { return id ? <Link className="citation-chip" href={query('/dashboard/contracts', {contract: text(id)})}>{text(id)}</Link> : null; }
function Points({value}: {value: unknown}) { return Array.isArray(value) && value.length ? <ul className="report-points">{value.map((v, i) => <li key={i}>{typeof v === 'object' ? <FieldValue value={v} /> : text(v)}</li>)}</ul> : <p className="muted-note">None recorded.</p>; }
function DraftText({value}: {value: unknown}) {
 return <div className="report-draft">{text(value, '').split(/\n\s*\n/).map((p, i) => <p key={i}>{p.split(/(\*\*[^*]+\*\*)/g).map((s, j) => s.startsWith('**') ? <strong key={j}>{s.slice(2,-2)}</strong> : s)}</p>)}</div>;
}
function Exposure({value}: {value: unknown}) {
 const exp = record(value); const currency = text(exp.currency, ''); const contracts = list(exp.contracts);
 return <><div className="report-metrics"><div><small>Expected exposure</small><strong>{formatMoney(exp.expected, currency)}</strong></div><div><small>Worst-case exposure</small><strong>{formatMoney(exp.worst_case, currency)}</strong></div>{exp.as_of ? <div><small>As of</small><strong>{dateText(exp.as_of)}</strong></div> : null}</div>
 {exp.note ? <p className="muted-note">{text(exp.note)}</p> : null}
 {contracts.length > 0 && <div className="report-agreements">{contracts.map(c => <article key={text(c.contract_id)}><header><Agreement id={c.contract_id} /><span>Term ends {dateText(c.term_end)}</span></header><div className="report-metrics"><div><small>Expected</small><strong>{formatMoney(c.expected, text(c.currency, currency))}</strong></div><div><small>Worst case</small><strong>{Object.keys(record(c.worst_case_by_currency)).length > 1 ? Object.entries(record(c.worst_case_by_currency)).map(([code, amount]) => formatMoney(amount, code)).join(' / ') : text(c.currency, currency) ? formatMoney(c.worst_case, text(c.currency, currency)) : number(c.worst_case) !== undefined ? number(c.worst_case)!.toLocaleString() + ' (currency not recorded)' : 'Not recorded'}</strong></div></div><p className="muted-note">Notice deadline: {c.notice_deadline ? dateText(c.notice_deadline) : 'Not recorded'}</p><details><summary>Calculation assumptions</summary><Points value={c.assumptions} /></details></article>)}</div>}
 {!contracts.length && exp.assumptions ? <details><summary>Calculation assumptions</summary><Points value={exp.assumptions} /></details> : null}</>;
}
function Actions({value}: {value: unknown}) {
 const actions = list(value);
 return actions.length ? <div className="report-actions">{actions.map((a, i) => <article key={text(a.id, String(i))}><header><span className="report-action-rank">{i+1}</span><Agreement id={a.contract_id} /><Status value={a.status} /><span className="report-kind">{text(a.kind, '').replaceAll('_', ' ')}</span></header><h4>{text(a.subject)}</h4><div className="report-action-meta">{a.deadline ? <span>Due {dateText(a.deadline)}</span> : null}{a.to ? <span>To: {text(a.to)}</span> : null}{a.priority !== undefined ? <span>Priority {text(a.priority)}</span> : null}<strong>{a.needs_human_approval === true ? 'Human approval required' : a.needs_human_approval === false ? 'Approval not required by recorded policy' : 'Approval requirement not recorded'}</strong></div><Citations values={a.citations} /><details><summary>Read draft and proposed changes</summary>{a.body_md ? <DraftText value={a.body_md} /> : <p className="muted-note">No draft text recorded.</p>}{list(a.redlines).map((r,j) => <section className="report-redline" key={j}><h4>Clause {text(r.clause_number)}</h4><div><small>Current wording</small><p>{text(r.before)}</p></div><div><small>Proposed wording</small><p>{text(r.after)}</p></div><p><strong>Reason: </strong>{text(r.reason)}</p></section>)}</details></article>)}</div> : <p className="muted-note">No actions recorded.</p>;
}
export function CounterpartyProfiles({value, currency = ''}: {value: unknown; currency?: string}) {
 return <div className="report-counterparties">{list(value).map((c,i) => <article key={i}><h4>{text(c.name)}</h4><div className="report-finding-agreements">{(Array.isArray(c.contracts) ? c.contracts : []).map(id => <Agreement key={text(id)} id={id} />)}</div><dl><div><dt>Violations</dt><dd>{text(c.violations)}</dd></div><div><dt>Late-payment events</dt><dd>{text(c.late_payment_events)}</dd></div><div><dt>Worst-case exposure</dt><dd>{Object.keys(record(c.worst_case_by_currency)).length > 1 ? Object.entries(record(c.worst_case_by_currency)).map(([code, amount]) => formatMoney(amount, code)).join(' / ') : text(c.currency, currency) ? formatMoney(c.worst_case, text(c.currency, currency)) : number(c.worst_case) !== undefined ? number(c.worst_case)!.toLocaleString() + ' (currency not recorded)' : 'Not recorded'}</dd></div></dl></article>)}</div>;
}
function Schedule({value}: {value: unknown}) {
 return list(value).length ? <div className="report-schedule">{list(value).map((e,i) => <article key={i}><time>{dateText(e.date)}</time><div><strong>{text(e.title ?? e.kind)}</strong><Agreement id={e.contract_id} /><Citations values={e.citation ? [e.citation] : e.citations} /></div><Status value={e.status} />{e.amount ? <strong>{formatMoney(e.amount)}</strong> : null}</article>)}</div> : <p className="muted-note">No deadlines recorded.</p>;
}
const HANDLED = new Set(['id','kind','title','contract_id','version','run_id','generated_at','as_of','completeness','workstreams','gaps','evidence_score','summary','summary_status','recovery_note','total_exposure','exposure','conflicts','risks','leading_risks','prioritized_actions','actions','counterparties','timeline','worst_case_projection','references','state']);
export function ReportBody({report}: {report: ApiRecord}) {
 const {timeZone} = useWorkspace(); const summary = record(report.summary);
 if (reportReadiness(report) === 'analysis_missing') return <div className="structured-report"><h2>{text(report.title, 'Contract report')}</h2><Agreement id={report.contract_id} /><div className="report-notice"><strong>Saved contract analysis is missing</strong><p>This is an earlier recovery placeholder, not a completed Synth report. Empty actions, deadlines and references do not establish that the agreement has no obligations or risks.</p><p>Generate a current report to extract and review this agreement. A new analysis cannot recreate an unsaved historical report.</p></div></div>;
 const extra = Object.fromEntries(Object.entries(report).filter(([k,v]) => !HANDLED.has(k) && v != null));
 return <div className="structured-report">
 <div className="report-overview"><div><h2>{text(report.title, report.kind === 'contract' ? 'Contract report' : 'Company risk report')}</h2><Agreement id={report.contract_id} /><Status value={report.completeness} /></div><dl>{report.generated_at ? <div><dt>Generated</dt><dd>{activityTimeText(report.generated_at,timeZone)}</dd></div> : null}{report.as_of ? <div><dt>Workspace date</dt><dd>{dateText(report.as_of)}</dd></div> : null}{report.version ? <div><dt>Contract version</dt><dd>{text(report.version)}</dd></div> : null}</dl></div>
 {report.recovery_note ? <p className="report-notice">{text(report.recovery_note)}</p> : null}
 {Object.keys(summary).length > 0 && <Section title="Executive summary"><Status value={report.summary_status ?? (summary.unavailable ? 'unavailable' : 'available')} /><p className="report-summary-text">{text(summary.executive_summary)}</p>{summary.reason ? <details><summary>Summary availability</summary><p>{text(summary.reason)}</p></details> : null}{Array.isArray(summary.key_risks) && summary.key_risks.length > 0 && <><h4>Key risks</h4><Points value={summary.key_risks} /></>}{Array.isArray(summary.recommended_next_steps) && summary.recommended_next_steps.length > 0 && <><h4>Recommended next steps</h4><Points value={summary.recommended_next_steps} /></>}</Section>}
 {report.total_exposure || report.exposure ? <Section title="Financial exposure" tone="amber"><Exposure value={report.total_exposure ?? report.exposure} /></Section> : null}
 {['conflicts','leading_risks','risks'].filter(k => list(report[k]).length).map(k => <Section title={k === 'conflicts' ? 'Cross-contract conflicts' : k === 'leading_risks' ? 'Leading risks' : 'Contract risks'} tone="rose" key={k}><ReportFindings findings={list(report[k])} /></Section>)}
 {report.prioritized_actions || report.actions ? <Section title="Prioritized actions" tone="teal"><Actions value={report.prioritized_actions ?? report.actions} /></Section> : null}
 {report.worst_case_projection || report.timeline ? <Section title="Deadlines and projection"><Schedule value={report.worst_case_projection ?? report.timeline} /></Section> : null}
 {report.counterparties ? <Section title="Counterparty profiles" tone="purple"><CounterpartyProfiles value={report.counterparties} currency={text(record(report.total_exposure).currency, '')} /></Section> : null}
 {(report.workstreams || report.gaps) ? <Section title="Review completion"><div className="report-workstreams">{Object.entries(record(report.workstreams)).map(([id,status]) => <div key={id}><strong>{id === 'cross' ? 'Cross-contract review' : id}</strong><Status value={status} /></div>)}</div>{report.gaps ? <p className="report-notice">{text(report.gaps)}</p> : null}</Section> : null}
 <details className="report-section"><summary>Clause references ({list(report.references).length})</summary>{list(report.references).map((c,i) => <article className="report-reference" key={i}><Citations values={[c]} />{c.quote ? <blockquote className="source-quote">{text(c.quote)}</blockquote> : null}</article>)}</details>
 {Object.keys(extra).length > 0 && <details className="report-section"><summary>Additional analysis and technical details</summary><FieldValue value={extra} /></details>}
 </div>;
}
