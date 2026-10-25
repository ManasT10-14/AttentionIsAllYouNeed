'use client';

import Link from 'next/link';
import { ArrowUpRight, ChevronDown, FileText, Info, Layers3, Workflow } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { list, number, query, record, text } from '@/lib/api';
import { useResource } from '@/lib/use-resource';
import { FieldValue, ResourceState, SourceBadge, Status } from './api-ui';
import { Panel } from './ui';

function coverage(value: unknown) {
  const score = number(value);
  return score === undefined ? undefined : Math.round(Math.max(0, Math.min(100, score <= 1 ? score * 100 : score)));
}

const budgetLabels: Record<string, string> = { agent_calls: 'Agent calls', tool_calls: 'Tool calls', tokens_in: 'Input tokens', tokens_out: 'Output tokens', usd: 'Cost · USD', fallbacks: 'Fallbacks' };

export function WorkPlan() {
  const resource = useResource('/api/runs?kind=analysis');
  const contracts = useResource('/api/contracts');
  const runs = Array.isArray(resource.data) ? list(resource.data) : list(resource.data, 'runs');
  const run = runs.find(item => item.kind === 'analysis') ?? runs[0];
  const streams = list(record(run?.workplan).workstreams);
  const names = new Map(list(contracts.data).map(item => [text(item.id), text(item.title, '')]));
  const scores = streams.map(item => coverage(item.evidence_score)).filter((score): score is number => score !== undefined);
  const average = scores.length ? Math.round(scores.reduce((total, score) => total + score, 0) / scores.length) : undefined;
  const sharedReason = streams.length > 1 && streams.every(item => item.reason === streams[0].reason) ? text(streams[0].reason, '') : '';
  const budget = record(run?.budget);
  const reduced = useReducedMotion();

  return <Panel className="workplan-panel">
    <header className="workplan-heading"><span className="workplan-symbol"><Workflow size={20} strokeWidth={1.6} /></span><div><h2>Analysis workplan</h2><p>Evidence behind each agreement. Progress at a glance.</p></div><Link className="workplan-run-link" href="/dashboard/observability">Inspect run<ArrowUpRight size={14} /></Link></header>
    <ResourceState resource={resource} empty={resource.data !== undefined && !run}>{run && <>
      <div className="workplan-overview">
        <div className="workplan-coverage-ring"><svg viewBox="0 0 90 90" aria-hidden="true"><circle cx="45" cy="45" r="36" /><motion.circle cx="45" cy="45" r="36" pathLength="100" initial={false} animate={{ strokeDasharray: `${average ?? 0} 100` }} transition={{ duration: reduced ? 0 : .65 }} /></svg><strong>{average === undefined ? '—' : average + '%'}<small>evidence</small></strong></div>
        <div className="workplan-overview-copy"><span className="workplan-overline">AGREEMENT REVIEW</span><h3>{streams.length} workstream{streams.length === 1 ? '' : 's'}<span><Status value={run.status} /></span></h3><p>{scores.length ? 'Average evidence coverage across ' + scores.length + ' scored workstream' + (scores.length === 1 ? '.' : 's.') : 'Evidence coverage has not been supplied yet.'}</p></div><SourceBadge value="analysis" />
      </div>
      <div className="workstream-list">{streams.map((stream, index) => {
        const contractId = text(stream.contract_id, '');
        const title = names.get(contractId) || (contractId ? contractId.replaceAll('_', ' ').replaceAll('-', ' ').replace(/^./, character => character.toUpperCase()) : 'Cross-contract review');
        const score = coverage(stream.evidence_score);
        return <article className="workstream-row" key={contractId || index}>
          <span className="workstream-document">{contractId ? <FileText size={18} strokeWidth={1.5} /> : <Layers3 size={18} strokeWidth={1.5} />}</span>
          <div className="workstream-info"><span className="workstream-index">WORKSTREAM {String(index + 1).padStart(2, '0')}</span>{contractId ? <Link href={query('/dashboard/contracts', { contract: contractId })}>{title}<ArrowUpRight size={12} /></Link> : <strong>{title}</strong>}{stream.reason && !sharedReason ? <p>{text(stream.reason)}</p> : null}</div>
          <div className="workstream-progress"><div><span>Evidence</span><strong>{score === undefined ? 'Not supplied' : score + '%'}</strong></div><div className="workstream-meter" role={score === undefined ? undefined : 'meter'} aria-label={'Evidence coverage for ' + title} aria-valuemin={score === undefined ? undefined : 0} aria-valuemax={score === undefined ? undefined : 100} aria-valuenow={score}><motion.i style={{ width: (score ?? 0) + '%' }} initial={{ scaleX: reduced ? 1 : 0 }} animate={{ scaleX: 1 }} transition={{ duration: reduced ? 0 : .7, delay: reduced ? 0 : index * .06 }} /></div></div>
          <div className="workstream-status"><Status value={stream.status} /></div>
          {list(stream.tasks).length > 0 && <details className="workstream-tasks"><summary>Inspect tasks<ChevronDown size={12} /></summary><FieldValue value={stream.tasks} /></details>}
        </article>;
      })}</div>
      {!streams.length && <p className="muted-note workplan-empty">No workstreams supplied for this run.</p>}
      {sharedReason && <div className="workplan-context"><Info size={14} /><p>{sharedReason}</p></div>}
      <details className="workplan-resources"><summary><span><Layers3 size={14} />Run resources</span><span>{number(budget.agent_calls) !== undefined ? budget.agent_calls + ' agent calls' : 'View usage'}<ChevronDown size={13} /></span></summary><dl>{Object.entries(budgetLabels).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{text(budget[key], '—')}</dd></div>)}</dl></details>
    </>}</ResourceState>
  </Panel>;
}
