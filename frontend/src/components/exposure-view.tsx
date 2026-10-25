'use client';
import Link from 'next/link';
import { useResource } from '@/lib/use-resource';
import { formatMoney, query, text, list, record, type Dashboard } from '@/lib/api';
import { useWorkspace } from './providers';
import { PageTitle, Panel, PanelTitle } from './ui';
import { Citations, ResourceState, SourceBadge } from './api-ui';
import { ExposureGauge } from './exposure-chart';
import { ExposureHeatmap } from './exposure-heatmap';
import { ClockControl } from './clock-control';

export function ExposureView() {
 const { date } = useWorkspace();
 const r = useResource<Dashboard>(query('/api/dashboard', { as_of: date }), 120); const contracts = useResource('/api/contracts');
 const names = new Map(list(contracts.data).map(c => [text(c.id ?? c.contract_id), text(c.title)]));
 const d = r.data; const cells = d?.heatmap?.cells ?? []; const currency = d?.exposure?.currency;
 return <><PageTitle eyebrow="FINANCIAL EXPOSURE" title="Find concentrated risk." description="See how much money is at stake, when, and which assumptions drive each estimate." /><ClockControl /><ResourceState resource={r}>{d && <>
 <Panel className="exposure-financial-panel"><PanelTitle title="Portfolio exposure" description="Expected and worst-case estimates at your selected date"><SourceBadge value="analysis" /></PanelTitle><ExposureGauge data={d} /></Panel>
 <Panel><PanelTitle title="Exposure by agreement" description="Read the complete calculation assumptions alongside each estimate." /><div className="exposure-agreements">{d.exposure?.contracts.map((c, i) => {
 const assumptions = Array.isArray(c.assumptions) ? c.assumptions.filter((a): a is string => typeof a === 'string' && Boolean(a.trim())) : typeof c.assumptions === 'string' && c.assumptions.trim() ? [c.assumptions] : [];
 const id = text(c.contract_id, String(i));
 return <article className="exposure-agreement" key={id}><header><div><small>{id}</small><h3><Link href={query('/dashboard/contracts', { contract: id })}>{text(c.title, names.get(id) ?? id)}</Link></h3></div><SourceBadge value="analysis" /></header><dl className="exposure-amounts"><div><dt>Expected</dt><dd>{formatMoney(c.expected, text(c.currency, currency))}</dd></div><div><dt>Worst case</dt><dd>{formatMoney(c.worst_case ?? c.amount, text(c.currency, currency))}</dd></div></dl><section className="exposure-assumptions"><h4>Calculation assumptions</h4>{assumptions.length ? <ul>{assumptions.map((a, n) => <li key={n}>{a}</li>)}</ul> : <p className="muted-note">No calculation assumptions were supplied for this agreement.</p>}</section>{list(c.lines).length > 0 && <details className="exposure-breakdown"><summary>View {list(c.lines).length} exposure components</summary>{list(c.lines).map((line, n) => <article key={n}><strong>{text(line.label)}</strong><span>{formatMoney(line.amount, text(record(line.amount).currency, currency))}</span>{line.citation ? <Citations values={[line.citation]} /> : null}</article>)}</details>}</article>;
 })}</div>{!d.exposure?.contracts.length && <p className="muted-note">No agreement exposure is available yet.</p>}</Panel>
 <ExposureHeatmap cells={cells} names={names} currency={currency} date={date} /></>}</ResourceState></>;
}
