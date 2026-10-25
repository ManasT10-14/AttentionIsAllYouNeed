'use client';
import { useState } from 'react';
import { useResource } from '@/lib/use-resource';
import { list, query, record, text } from '@/lib/api';
import { useWorkspace } from './providers';
import { Button,PageTitle,Panel,PanelTitle } from './ui';
import { CitationChip,DownloadLink,FieldValue,MutationFeedback,ResourceState,SourceBadge,useMutation } from './api-ui';
export function ReportsView() {
 const [contract,setContract]=useState(''); const {canAdmin,demo}=useWorkspace(); const m=useMutation();
 const path=contract?query('/api/reports/contract',{contract_id:contract}):'/api/reports/company';
 const r=useResource(path);const counterparties=useResource('/api/insights/counterparties');const report=record(r.data);
 return <><PageTitle eyebrow="REPORTS" title="The complete picture." description="Executive summary, key terms, risks, actions and source references."><DownloadLink path={path+(path.includes('?')?'&':'?')+'format=pdf'}>Download PDF</DownloadLink>{canAdmin && <Button disabled={m.pending || demo} onClick={()=>void m.run('/api/reports/refresh')}>Regenerate reports</Button>}</PageTitle><Panel><label className="input-label">Contract ID · leave empty for company report<input className="input" value={contract} onChange={e=>setContract(e.target.value)} placeholder="Company-wide report" /></label><MutationFeedback mutation={m} /><ResourceState resource={r}><div className="report-content"><PanelTitle title={contract?'Contract report':'Company report'}><SourceBadge value="analysis" /></PanelTitle>{report.completeness ? <section className="report-completeness"><h3>Completeness</h3><FieldValue value={report.completeness} /></section> : null}{Object.entries(report).filter(([key])=>!['references','completeness'].includes(key)).map(([key,value])=><section key={key}><h3>{key.replaceAll('_',' ')}</h3><FieldValue value={value} /></section>)}<section><h3>References</h3>{list(report.references).map((ref,i)=><div key={i}><CitationChip value={ref} /><blockquote className="source-quote">{text(ref.quote,'')}</blockquote></div>)}{!list(report.references).length && <p className="muted-note">No references returned.</p>}</section></div></ResourceState></Panel><Panel><PanelTitle title="Counterparty risk profiles" description="Exposure, violations and late-payment events by party" /><SourceBadge value="analysis" /><ResourceState resource={counterparties}><FieldValue value={counterparties.data} /></ResourceState></Panel></>;
}
