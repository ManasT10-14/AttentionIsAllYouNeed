'use client';
import Link from 'next/link';
import { formatMoney, record, type Dashboard } from '@/lib/api';
import { Panel, PanelTitle } from './ui';
import { SourceBadge } from './api-ui';
export function ExposureGauge({ data }: { data: Dashboard }) {
 const exposure = data.exposure;
 if (!exposure) return <p className="muted-note">Exposure has not been returned by the backend.</p>;
 const expected = typeof exposure.expected === 'number' ? exposure.expected : Number(record(exposure.expected).amount);
 const worst = typeof exposure.worst_case === 'number' ? exposure.worst_case : Number(record(exposure.worst_case).amount);
 const ratio = Number.isFinite(expected) && worst > 0 ? Math.min(1,Math.max(0,expected / worst)) : 0;
 return <div className="live-exposure-gauge"><svg viewBox="0 0 240 145" role="img" aria-label={'Expected ' + formatMoney(exposure.expected,exposure.currency) + ' within worst case ' + formatMoney(exposure.worst_case,exposure.currency)}><path d="M25 120 A95 95 0 0 1 215 120" fill="none" stroke="var(--chart-track)" strokeWidth="15" strokeLinecap="round" pathLength="100" /><path d="M25 120 A95 95 0 0 1 215 120" fill="none" stroke="var(--chart-accent)" strokeWidth="15" strokeLinecap="round" pathLength="100" strokeDasharray={ratio * 100 + ' 100'} /><text x="120" y="98" textAnchor="middle">{formatMoney(exposure.expected,exposure.currency)}</text><text className="gauge-caption" x="120" y="119" textAnchor="middle">expected exposure</text></svg><div className="gauge-values"><div><span>Worst case</span><strong>{formatMoney(exposure.worst_case,exposure.currency)}</strong></div><div><span>Currency</span><strong>{exposure.currency}</strong></div></div><SourceBadge value="analysis" /></div>;
}
export function ExposureSummary({ data }: { data: Dashboard }) {
 return <Panel><PanelTitle title="Financial exposure" description="Backend estimates at the selected simulated date"><SourceBadge value="analysis" /></PanelTitle><ExposureGauge data={data} /><Link className="text-link" href="/dashboard/exposure">Inspect exposure and assumptions →</Link></Panel>;
}
