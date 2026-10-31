'use client';
import Link from 'next/link';
import { useState } from 'react';
import { useResource } from '@/lib/use-resource';
import { useWorkspace } from './providers';
import { Button,PageTitle,Panel,PanelTitle,Badge } from './ui';
import { FieldValue,ResourceState } from './api-ui';
import { UploadSheet } from './upload-sheet';
const sections={
 evals:{title:'Evaluation workspace',description:'Quality, retrieval accuracy and regression checks.',cards:[['Quality scorecards','Citation faithfulness, extraction accuracy, conflict recall and answer quality.'],['Run history & comparison','Metric trends and A/B comparisons by model and prompt version.'],['Golden datasets','Test-case drill-down, retrieval evaluation and per-agent quality.']]},
 security:{title:'Security workspace',description:'Guard events, tool permissions and approval auditing.',cards:[['Guard events & quarantine','Injection inspection, policy violations and blocked inputs.'],['Permission matrix','Agent scopes and approval requirements from the current tool registry.'],['Policies & PII review','Permission-gated redaction previews and super-admin policy settings.']]},
 admin:{title:'Company administration',description:'Company context and a view of upcoming administration controls.',cards:[['Users & roles','Invites and role assignment when the backend management endpoints are available.'],['Models & budgets','Per-agent models, fallback chains and budget settings.'],['Integrations','Gmail, LangSmith and webhook settings managed by the backend.']]}
};
export function FutureView({section}:{section:keyof typeof sections}) {
 const s=sections[section];const {canAdmin}=useWorkspace();const [upload,setUpload]=useState(false);
 const current=useResource(section==='security'?'/api/tools':section==='admin'?'/api/observability':null);
 return <><PageTitle eyebrow="PLANNED WORKSPACE" title={s.title} description={s.description}>{section==='admin'&&canAdmin&&<Button onClick={()=>setUpload(true)}>Upload company context</Button>}</PageTitle>{section==='admin'&&canAdmin&&<Panel><PanelTitle title="Internal security review"/><p>Protection runs automatically. Administrators can inspect detections and review quarantined events here.</p><Link className="button button-secondary" href="/dashboard/security">Review security and quarantine</Link></Panel>}<div className="future-banner"><Badge tone="amber">Planned backend endpoints</Badge><p>These views are prepared for the next integration. Unavailable operations are not sent to the backend.</p></div><div className="future-grid">{s.cards.map(([title,description])=><Panel key={title}><PanelTitle title={title}/><p>{description}</p><Button variant="secondary" disabled>Awaiting backend endpoint</Button></Panel>)}</div>{section!=='evals'&&<Panel><PanelTitle title={section==='security'?'Current tool permissions':'Current limits and providers'} description="Read-only data from endpoints that already exist"/><ResourceState resource={current}><FieldValue value={current.data}/></ResourceState></Panel>}<UploadSheet open={upload} onOpenChange={setUpload} company/></>;
}
