'use client';
import Link from 'next/link';
import { Activity, CalendarDays, FileText } from 'lucide-react';
import { useWorkspace } from './providers';
import { useResource } from '@/lib/use-resource';
import { dateText, query, text, type Dashboard } from '@/lib/api';
import { Badge, PageTitle, Panel, PanelTitle, TextLink } from './ui';
import { AnimatedMetric } from './animated-metric';
import { Citations, ResourceState, SourceBadge, Status } from './api-ui';
import { ClockControl } from './clock-control';
import { ExposureSummary } from './exposure-chart';
import { GmailPill } from './dashboard-shell';
import { WorkPlan } from './work-plan';
export function OverviewView() {
 const { date,session,demo } = useWorkspace();
 const r = useResource<Dashboard>(query('/api/dashboard',{ as_of: date }),180);
 const d = r.data;
 return <><PageTitle eyebrow="PORTFOLIO OVERVIEW" title={'A clearer picture' + (session?.user.name ? ', ' + session.user.name.split(' ')[0] : '') + '.'} description="Your contracts, current risks and next decisions, backed by evidence."><GmailPill /></PageTitle><ClockControl /><ResourceState resource={r}>{d && <><div className="stats-grid"><Panel className="stat-card"><div className="stat-heading"><span>TOP ALERTS</span><Badge tone="amber">Review queue</Badge></div><AnimatedMetric value={d.alerts?.length ?? 0} /><p>Alerts returned at {dateText(date)}</p><TextLink href="/dashboard/actions">Review alerts</TextLink></Panel><Panel className="stat-card"><div className="stat-heading"><span>CONTRACT HEALTH</span><FileText size={16} /></div><AnimatedMetric value={Object.keys(d.health ?? {}).length} /><p>Contracts with health results</p><SourceBadge value="analysis" /></Panel><Panel className="stat-card"><div className="stat-heading"><span>SIMULATED DATE</span><CalendarDays size={16} /></div><strong className="date-metric">{dateText(date)}</strong><p>{demo ? 'Sample projections' : 'Backend financial projections'}</p></Panel><Panel className="stat-card"><div className="stat-heading"><span>EXPOSURE VIEWS</span><Activity size={16} /></div><AnimatedMetric value={d.exposure?.contracts.length ?? 0} /><p>Contracts with exposure estimates</p><TextLink href="/dashboard/exposure">Inspect assumptions</TextLink></Panel></div><div className="overview-columns"><div className="overview-main"><Panel><PanelTitle title="Priority alerts" description="Why each alert matters and the source behind it" /><div className="live-alert-list">{(d.alerts ?? []).slice(0,10).map((a,i) => <article key={text(a.id,String(i))}><header><strong>{text(a.title)}</strong><Status value={a.severity} severity /></header><p>{text(a.why)}</p><div><SourceBadge value={a.source} /><span>{dateText(a.due_date)}</span></div><Citations values={a.citations} /></article>)}{!d.alerts?.length && <div className="all-clear"><strong>No priority alerts returned.</strong><p>Use the clock to look ahead.</p></div>}</div><TextLink href="/dashboard/actions">Open alerts and actions</TextLink></Panel><WorkPlan /></div><aside className="overview-aside"><ExposureSummary data={d} /><Panel><PanelTitle title="Contract health" description="Backend scores; absent values remain unanalysed" /><div className="health-tiles">{Object.entries(d.health ?? {}).map(([contract,score]) => <Link key={contract} href={'/dashboard/contracts?contract=' + encodeURIComponent(contract)}><span>{contract}</span><strong>{score === null ? 'Not analysed' : score + '/100'}</strong></Link>)}</div>{!Object.keys(d.health ?? {}).length && <p className="muted-note">No health scores returned yet.</p>}<SourceBadge value="analysis" /></Panel></aside></div></>}</ResourceState></>;
}
