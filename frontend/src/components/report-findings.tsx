'use client';
import Link from 'next/link';
import { list, number, query, text, type ApiRecord } from '@/lib/api';
import { Citations, Status } from './api-ui';
export function ReportFindings({ findings }: { findings: ApiRecord[] }) {
 if (!findings.length) return <p className="muted-note">None recorded.</p>;
 return <div className="report-findings">{findings.map((f, i) => {
  const likelihood = number(f.likelihood);
  const contracts = [...new Set([f.contract_id, ...(Array.isArray(f.other_contract_ids) ? f.other_contract_ids : []), ...list(f.citations).map(c => c.contract_id)].filter((c): c is string => typeof c === 'string' && c !== 'cross'))];
  return <article className="report-finding" key={text(f.id, String(i))}>
   <header><span className="report-finding-index">{i + 1}</span><Status value={f.severity} severity /><Status value={f.status} />{likelihood !== undefined && <small>Likelihood {Math.round(likelihood * 100)}%</small>}</header>
   <p className="report-finding-claim">{text(f.claim ?? f.title)}</p>
   <div className="report-finding-agreements">{contracts.map(c => <Link className="citation-chip" key={c} href={query('/dashboard/contracts', {contract: c})}>{c}</Link>)}</div>
   <Citations values={f.citations} />
   <details><summary>Read evidence and review rationale</summary>
    {f.attack_path ? <section><h4>Risk scenario</h4><p>{text(f.attack_path)}</p></section> : null}
    {list(f.debate).map((d, j) => <section className="report-finding-decision" key={j}><header><strong>{text(d.by, 'Review')}</strong><Status value={d.verdict ?? d.stance} /></header><p>{text(d.rationale ?? d.response ?? d.argument)}</p></section>)}
    {!list(f.debate).length && !f.attack_path && <p className="muted-note">No additional review rationale was saved.</p>}
    {list(f.citations).filter(c => c.quote).map((c, j) => <blockquote className="source-quote" key={j}>{text(c.quote)}</blockquote>)}
    <Link className="text-link" href={query('/dashboard/agent-review', {finding: text(f.id, '')})}>Open finding and decisions</Link>
   </details>
  </article>;
 })}</div>;
}
