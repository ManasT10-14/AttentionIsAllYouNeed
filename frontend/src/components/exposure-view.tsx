'use client';
import Link from 'next/link';
import { useResource } from '@/lib/use-resource';
import { formatMoney,query,text,list,type Dashboard } from '@/lib/api';
import { useWorkspace } from './providers';
import { PageTitle,Panel,PanelTitle } from './ui';
import { ResourceState,SourceBadge,FieldValue } from './api-ui';
import { ExposureGauge } from './exposure-chart';
import { ExposureHeatmap } from './exposure-heatmap';
import { ClockControl } from './clock-control';
export function ExposureView() {
 const {date}=useWorkspace();
 const r=useResource<Dashboard>(query('/api/dashboard',{as_of:date}),120);const contracts=useResource('/api/contracts');
 const names=new Map(list(contracts.data).map(c=>[text(c.id),text(c.title)]));
 const d=r.data;const cells=d?.heatmap?.cells??[];const currency=d?.exposure?.currency;
 return <><PageTitle eyebrow="FINANCIAL EXPOSURE" title="Find concentrated risk." description="See how much money is at stake, when, and in which agreements. Click the heatmap to see why."/><ClockControl/><ResourceState resource={r}>{d&&<>
 <Panel className="exposure-financial-panel"><PanelTitle title="Portfolio exposure" description="Expected and worst-case estimates at your selected date"><SourceBadge value="analysis"/></PanelTitle><div className="exposure-two-column"><ExposureGauge data={d}/><div className="table-scroll"><table className="data-table exposure-contract-table"><thead><tr><th>Agreement</th><th>Exposure</th><th>Assumptions</th></tr></thead><tbody>{d.exposure?.contracts.map((c,i)=><tr key={text(c.contract_id,String(i))}><td><Link href={query('/dashboard/contracts',{contract:text(c.contract_id)})}>{text(c.title,names.get(text(c.contract_id))??text(c.contract_id))}</Link></td><td>{formatMoney(c.amount??c.worst_case,currency)}</td><td><details><summary>View assumptions</summary><FieldValue value={c.assumptions}/></details></td></tr>)}</tbody></table></div></div></Panel>
 <ExposureHeatmap cells={cells} names={names} currency={currency} date={date}/></>}</ResourceState></>;
}
