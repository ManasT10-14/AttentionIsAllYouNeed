'use client';
import Link from 'next/link';
import { useResource } from '@/lib/use-resource';
import { runTitle } from '@/lib/run-presentation';
import { list,number,record,text } from '@/lib/api';
import { SourceBadge,Status } from './api-ui';
export function RunIndicator() {
 const runs=useResource('/api/runs');
 const rows=Array.isArray(runs.data)?list(runs.data):list(runs.data,'runs');
 const current=rows.find(r=>['running','pending'].includes(text(r.status,'')));
 const observation=useResource(current?'/api/observability':null);
 if(!current)return null;
 const budget=record(current.budget);const limits=record(record(observation.data).limits);
 const calls=number(budget.agent_calls);const maxCalls=number(limits.max_agent_calls);const usd=number(budget.usd);const maxUsd=number(limits.max_usd);
 return <aside className="run-indicator" aria-label="Active analysis run"><div><Status value={current.status}/><strong>{runTitle(current)}</strong><SourceBadge value="analysis"/><Link className="text-link" href={'/dashboard/workflow?run=' + encodeURIComponent(text(current.id))}>Inspect progress →</Link></div><div className="run-budget"><label>Agent calls {text(calls)}{maxCalls!==undefined?' / '+maxCalls:''}{maxCalls!==undefined&&calls!==undefined&&<progress value={calls} max={Math.max(1,maxCalls)}/>}</label><label>USD {text(usd)}{maxUsd!==undefined?' / '+maxUsd:''}{maxUsd!==undefined&&usd!==undefined&&<progress value={usd} max={Math.max(.01,maxUsd)}/>}</label></div></aside>;
}
