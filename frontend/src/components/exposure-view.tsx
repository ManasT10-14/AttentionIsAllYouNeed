'use client';
import Link from 'next/link';
import { useState } from 'react';
import { ArrowUpRight, ChevronDown, FileText } from 'lucide-react';
import { useResource } from '@/lib/use-resource';
import { dateText, formatMoney, query, text, list, record, type Dashboard } from '@/lib/api';
import { useWorkspace } from './providers';
import { Badge, PageTitle, Panel, PanelTitle } from './ui';
import { Citations, ResourceState, SourceBadge } from './api-ui';
import { ExposureGauge } from './exposure-chart';
import { ExposureHeatmap } from './exposure-heatmap';
import { ClockControl } from './clock-control';

export function ExposureView() {
 const { date } = useWorkspace(); const [expanded, setExpanded] = useState<string | null>(null);
 const r = useResource<Dashboard>(query('/api/dashboard', { as_of: date }), 120); const contracts = useResource('/api/contracts');
 const names = new Map(list(contracts.data).map(c => [text(c.id ?? c.contract_id), text(c.title)]));
 const d = r.data; const cells = d?.heatmap?.cells ?? []; const currency = d?.exposure?.currency;
 const money = (value: unknown, code: string) => value === undefined || value === null ? 'Not quantified' : formatMoney(value, code);
 return <><PageTitle eyebrow="FINANCIAL EXPOSURE" title="Find concentrated risk." description="See how much money is at stake, when, and which assumptions drive each estimate." /><ClockControl /><ResourceState resource={r}>{d && <>
 <Panel className="exposure-financial-panel"><PanelTitle title="Portfolio exposure" description="Expected and worst-case estimates at your selected date"><SourceBadge value="analysis" /></PanelTitle><ExposureGauge data={d} /></Panel>
 <Panel className="exposure-register"><PanelTitle title="Exposure by agreement" description="Compare estimates at a glance, then expand an agreement to inspect its calculation basis."><Badge>{d.exposure?.contracts.length ?? 0} agreements</Badge></PanelTitle><div className="exposure-register-list">{d.exposure?.contracts.map((c, i) => {
 const assumptions = Array.isArray(c.assumptions) ? c.assumptions.filter((a): a is string => typeof a === 'string' && Boolean(a.trim())) : typeof c.assumptions === 'string' && c.assumptions.trim() ? [c.assumptions] : [];
 const id = text(c.contract_id, String(i)); const open = expanded === null ? i === 0 : expanded === id; const code = text(c.currency, currency);
 return <article className={'exposure-register-row' + (open ? ' is-open' : '')} key={id}><div className="exposure-row-heading"><span className="exposure-row-icon"><FileText size={21} strokeWidth={1.6} /></span><div className="exposure-row-name"><small>{id}</small><h3><Link href={query('/dashboard/contracts', { contract: id })}>{text(c.title, names.get(id) ?? id)}<ArrowUpRight size={13} /></Link></h3><div className="exposure-row-dates">{c.notice_deadline ? <span>Notice by {dateText(c.notice_deadline)}</span> : null}{c.term_end ? <span>Term ends {dateText(c.term_end)}</span> : null}</div></div><dl className="exposure-row-money"><dt>Expected</dt><dd data-missing={c.expected === undefined || c.expected === null ? true : undefined}>{money(c.expected, code)}</dd></dl><dl className="exposure-row-money worst"><dt>Worst case</dt><dd data-missing={c.worst_case === undefined && c.amount === undefined ? true : undefined}>{money(c.worst_case ?? c.amount, code)}</dd></dl><button className="exposure-basis-toggle" aria-label={(open ? 'Hide' : 'Show') + ' calculation basis for ' + text(c.title, names.get(id) ?? id)} aria-expanded={open} aria-controls={'exposure-basis-' + i} onClick={() => setExpanded(open ? '' : id)}><span>{open ? 'Hide basis' : 'View basis'}</span><ChevronDown size={16} /></button></div>
 {!open && <p className="exposure-basis-preview">{assumptions[0] ?? 'No calculation assumptions supplied.'}{assumptions.length > 1 && <span> +{assumptions.length - 1} more</span>}</p>}
 {open && <div className="exposure-calculation-basis" id={'exposure-basis-' + i}><section><h4>Calculation assumptions</h4>{assumptions.length ? <ol>{assumptions.map((a, n) => <li key={n}>{a}</li>)}</ol> : <p className="muted-note">No calculation assumptions were supplied for this agreement.</p>}</section>{list(c.lines).length > 0 && <section className="exposure-register-components"><h4>Exposure components</h4>{list(c.lines).map((line, n) => <article key={n}><div><strong>{text(line.label)}</strong>{line.citation ? <Citations values={[line.citation]} /> : null}</div><span>{formatMoney(line.amount, text(record(line.amount).currency, currency))}</span></article>)}</section>}</div>}</article>;
 })}</div>{!d.exposure?.contracts.length && <p className="muted-note">No agreement exposure is available yet.</p>}</Panel>
 <ExposureHeatmap cells={cells} names={names} currency={currency} date={date} /></>}</ResourceState></>;
}
