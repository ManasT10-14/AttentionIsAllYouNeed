'use client';
import { useState, type CSSProperties } from 'react';
import Link from 'next/link';
import { ArrowUpRight, RotateCcw, X } from 'lucide-react';
import { useResource } from '@/lib/use-resource';
import { formatMoney, list, query, record, text } from '@/lib/api';
import { heatScaleMaximum } from '@/lib/heatmap';
import type { HeatCell } from '@/lib/heatmap';
import { Panel } from './ui';
import { CitationChip, ResourceState } from './api-ui';
import '@/app/insights-views.css';

export function monthLabel(month: string) { const date = new Date(month + '-01T00:00:00Z'); return Number.isNaN(date.getTime()) ? month : date.toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' }); }
function compact(amount: number, currency?: string) {
  try { return new Intl.NumberFormat(currency === 'INR' ? 'en-IN' : 'en-US', { style: 'currency', currency: currency || 'USD', notation: 'compact', maximumFractionDigits: 1 }).format(amount); }
  catch { return String(Math.round(amount)); }
}
const shade = (amount: number, max: number) => amount <= 0 ? 0 : Math.min(1, 0.14 + 0.86 * Math.sqrt(amount / max));
const sum = (cells: HeatCell[]) => cells.reduce((t, c) => t + c.amount, 0);

export function ExposureHeatmap({ cells, names, currency, date }: { cells: HeatCell[]; names: Map<string, string>; currency?: string; date: string }) {
  const [by, setBy] = useState<'contract' | 'type'>('contract');
  const [contract, setContract] = useState(''); const [type, setType] = useState(''); const [month, setMonth] = useState('');
  const [pick, setPick] = useState<{ row: string; month: string } | null>(null);
  const key = (c: HeatCell) => by === 'contract' ? c.contract_id : c.clause_type;
  const label = (row: string) => by === 'contract' ? names.get(row) ?? row : row.replaceAll('_', ' ');
  const visible = cells.filter(c => (!contract || c.contract_id === contract) && (!type || c.clause_type === type) && (!month || c.month === month));
  const rows = [...new Set(visible.map(key))]; const months = [...new Set(visible.map(c => c.month))].sort();
  const max = heatScaleMaximum(cells, by); const grand = sum(visible); const filters = Boolean(contract || type || month);
  const clear = () => { setContract(''); setType(''); setMonth(''); setPick(null); };
  const timeline = useResource(pick ? query('/api/timeline', { as_of: date }) : null);
  const lines = list(timeline.data && record(timeline.data).contracts).flatMap(c => list(record(c.exposure).lines)).filter(l => pick && text(l.month) === pick.month && (by === 'contract' ? l.contract_id === pick.row : l.clause_type === pick.row) && (!contract || l.contract_id === contract) && (!type || l.clause_type === type));
  const picked = pick ? sum(visible.filter(c => key(c) === pick.row && c.month === pick.month)) : 0;
  return <Panel className="hm">
    <header className="hm-head"><div><p className="eyebrow">EXPOSURE HEATMAP</p><h2>When and where will money be at stake?</h2><p>Each square is the money tied to one {by === 'contract' ? 'agreement' : 'clause type'} in one month, as of the simulated date. <b>Darker means more money.</b> Click a square to see what is behind it.</p></div>
      <div className="matrix-group-toggle" role="group" aria-label="Group rows by"><button aria-pressed={by === 'contract'} className={by === 'contract' ? 'active' : ''} onClick={() => { setBy('contract'); setPick(null); }}>By agreement</button><button aria-pressed={by === 'type'} className={by === 'type' ? 'active' : ''} onClick={() => { setBy('type'); setPick(null); }}>By clause type</button></div></header>
    <div className="hm-filters"><label>Agreement<select value={contract} onChange={e => { setContract(e.target.value); setPick(null); }}><option value="">All</option>{[...new Set(cells.map(c => c.contract_id))].map(id => <option value={id} key={id}>{names.get(id) ?? id}</option>)}</select></label><label>Clause type<select value={type} onChange={e => { setType(e.target.value); setPick(null); }}><option value="">All</option>{[...new Set(cells.map(c => c.clause_type))].map(t => <option key={t} value={t}>{t.replaceAll('_', ' ')}</option>)}</select></label><label>Month<select value={month} onChange={e => { setMonth(e.target.value); setPick(null); }}><option value="">All</option>{[...new Set(cells.map(c => c.month))].sort().map(m => <option key={m} value={m}>{monthLabel(m)}</option>)}</select></label>{filters && <button className="hm-clear" onClick={clear}><RotateCcw size={12} />Clear filters</button>}<span className="hm-total">Total shown <strong>{formatMoney(grand, currency)}</strong></span></div>
    {!visible.length ? <div className="empty-state"><h3>Nothing at stake in this view.</h3><p>Try another date or clear the filters.</p>{filters && <button className="hm-clear" onClick={clear}>Clear filters</button>}</div> : <>
      <div className="hm-scroll"><table className="hm-grid"><caption className="sr-only">Exposure by {by === 'contract' ? 'agreement' : 'clause type'} and month</caption>
        <thead><tr><th className="hm-corner"><span>{by === 'contract' ? 'Agreement' : 'Clause type'} ↓</span><span>Month →</span></th>{months.map(m => <th key={m} scope="col">{monthLabel(m)}</th>)}<th scope="col" className="hm-sum">Row total</th></tr></thead>
        <tbody>{rows.map(row => <tr key={row}><th scope="row" title={label(row)}>{label(row)}</th>{months.map(m => {
          const amount = sum(visible.filter(c => key(c) === row && c.month === m)); const on = pick?.row === row && pick.month === m; const t = shade(amount, max);
          const full = label(row) + ' · ' + monthLabel(m) + ': ' + (amount ? formatMoney(amount, currency) + ' (' + Math.round(amount / grand * 100) + '% of total shown)' : 'nothing at stake');
          return <td key={m}>{amount > 0 ? <button className={'hm-cell' + (on ? ' on' : '')} data-hi={t > .55 ? '' : undefined} style={{ '--t': t } as CSSProperties} title={full} aria-label={full} aria-pressed={on} onClick={() => setPick(on ? null : { row, month: m })}>{compact(amount, currency)}</button> : <span className="hm-cell empty" title={full} aria-label={full}>–</span>}</td>;
        })}<td className="hm-sum">{formatMoney(sum(visible.filter(c => key(c) === row)), currency)}</td></tr>)}</tbody>
        {rows.length > 1 && <tfoot><tr><th scope="row">All {by === 'contract' ? 'agreements' : 'clause types'}</th>{months.map(m => <td key={m} className="hm-sum">{compact(sum(visible.filter(c => c.month === m)), currency)}</td>)}<td className="hm-sum">{formatMoney(grand, currency)}</td></tr></tfoot>}
      </table></div>
      <footer className="hm-legend"><span className="hm-key"><i className="hm-swatch empty" />Nothing at stake</span><span className="hm-key"><small>Less</small><i className="hm-ramp" /><small>More ({compact(max, currency)} in the busiest square)</small></span></footer>
      <p className="hm-note">Money = scheduled payments, renewal lock-ins and accrued or potential penalties (worst case). Colour is relative to the busiest square across all filters, so it stays comparable while you filter. Currency: {currency ?? 'as reported'}.</p>
      {pick && <section className="hm-detail" aria-live="polite"><header><div><h3>{label(pick.row)} · {monthLabel(pick.month)}</h3><p>{formatMoney(picked, currency)} at stake. These are the items and clauses behind this square.</p></div><button className="icon-button" aria-label="Close details" onClick={() => setPick(null)}><X size={15} /></button></header>
        <ResourceState resource={timeline} empty={timeline.data !== undefined && !lines.length}><ul>{lines.map((l, i) => <li key={i}><div><strong>{text(l.label)}</strong><small>{names.get(text(l.contract_id)) ?? text(l.contract_id)} · {text(l.clause_type).replaceAll('_', ' ')}</small></div><b>{formatMoney(l.amount)}</b><CitationChip value={l.citation} /></li>)}</ul></ResourceState>
        <Link className="text-link" href={query('/dashboard/timeline', { contract_id: by === 'contract' ? pick.row : contract || undefined, clause_type: by === 'type' ? pick.row : type || undefined, month: pick.month })}>Open these obligations in the timeline <ArrowUpRight size={12} /></Link></section>}
    </>}
  </Panel>;
}
