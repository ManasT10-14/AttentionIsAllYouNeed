'use client';
import { useEffect, useRef, useState } from 'react';
import { useSearchParams,useRouter } from 'next/navigation';
import { ArrowRight,Search,FileText,PenLine } from 'lucide-react';
import { useResource } from '@/lib/use-resource';
import { actionSecurity, validActionRecipients } from '@/lib/action-security';
import { dateText, dateTimeText, daysBetween, deliveryOperation, list, query, record, text } from '@/lib/api';
import { useWorkspace } from './providers';
import { Badge, Button, PageTitle, Panel, PanelTitle, Sheet } from './ui';
import { AmendmentDetail, AmendmentSummary } from './amendment-card';
import { CitationChip, Citations, DownloadLink, FieldValue, MutationFeedback, ResourceState, SourceBadge, Status, TraceLink, useMutation } from './api-ui';
/** Due-date wording relative to the simulated clock (never the real date). */
function dueNote(due: unknown, now: string, done = false) {
 const s = text(due,'').slice(0,10); if (!s || done) return '';
 const d = daysBetween(now,s);
 return d < 0 ? 'Overdue by ' + -d + ' day' + (d === -1 ? '' : 's') : d === 0 ? 'Due today' : 'Due in ' + d + ' day' + (d === 1 ? '' : 's');
}
export function ActionsView() {
 const { date,canAdmin,demo } = useWorkspace(); const router = useRouter(); const search = useSearchParams(); const selected = search.get('draft');
 const [tab,setTab] = useState('actions'); const [closed,setClosed] = useState(false); const [actionQuery,setActionQuery] = useState(''); const [actionStatus,setActionStatus] = useState('');
 const a = useResource('/api/actions'); const alerts = useResource(query('/api/alerts',{as_of:date,include_closed:closed}),180); const violations = useResource(tab === 'violations' ? '/api/violations' : null); const m = useMutation();
 const amendmentsFor = (alert: Record<string,unknown>) => { const nums = new Set(list(alert.citations).map(c => text(c.clause_number,''))); return actions.filter(x => x.kind === 'amendment' && x.contract_id === alert.contract_id && list(x.redlines).some(r => nums.has(text(r.clause_number,'')))); };
 const actions = Array.isArray(a.data) ? list(a.data) : list(a.data,'actions'); const alertRows = Array.isArray(alerts.data) ? list(alerts.data) : list(alerts.data,'alerts'); const vRows = Array.isArray(violations.data) ? list(violations.data) : list(violations.data,'violations');
 return <><PageTitle eyebrow="ALERTS & ACTIONS" title="Turn evidence into decisions." description="Review why an alert exists, inspect a draft, and approve before sending."><DownloadLink path="/api/export/actions.csv">Export actions CSV</DownloadLink>{canAdmin && <Button variant="secondary" disabled={m.pending || demo} onClick={() => void m.run('/api/digest/draft')}>Draft daily digest</Button>}</PageTitle><div className="segmented-control page-tabs">{['actions','alerts','violations'].map(t => <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>)}</div><MutationFeedback mutation={m} />{tab === 'actions' && <Panel className="action-list-panel"><div className="action-list-toolbar"><div><h2>Action queue</h2><p>Review the draft, check the source, then decide.</p></div><label className="action-list-search"><Search size={14}/><input aria-label="Search action drafts" placeholder="Search actions…" value={actionQuery} onChange={e=>setActionQuery(e.target.value)}/></label><select aria-label="Filter action status" value={actionStatus} onChange={e=>setActionStatus(e.target.value)}><option value="">All statuses</option>{[...new Set(actions.map(a=>text(a.status)))].map(s=><option key={s} value={s}>{s}</option>)}</select></div><ResourceState resource={a} empty={a.data!==undefined&&!actions.length}><div className="action-rows"><div className="action-row-labels"><span>Action</span><span>Agreement</span><span>Deadline</span><span>Status</span><span/></div>{actions.filter(action=>(!actionStatus||action.status===actionStatus)&&(!actionQuery||JSON.stringify(action).toLowerCase().includes(actionQuery.toLowerCase()))).map(action=><article className="action-row" key={text(action.id)}><div className="action-row-main"><span className={'action-row-icon '+(action.kind==='amendment'?'is-amendment':'')}>{action.kind==='amendment'?<PenLine size={17}/>:<FileText size={17}/>}</span><div><button className="action-subject" onClick={()=>router.push(query('/dashboard/actions',{draft:text(action.id)}))}>{text(action.subject)}</button><small>{text(action.kind).replaceAll('_',' ')}{action.needs_approval===true?' · Approval required':''}</small>{action.kind==='amendment'&&<AmendmentSummary action={action}/>}</div></div><span className="action-row-contract" title={text(action.contract_id)}>{text(action.contract_id)}</span><span className="action-row-date">{dateText(action.deadline)}{['draft'].includes(text(action.status))&&<small className={'due-note'+(dueNote(action.deadline,date).startsWith('Overdue')?' is-late':'')}>{dueNote(action.deadline,date)}</small>}</span><div className="action-row-status"><Status value={action.status}/></div><Button variant="ghost" className="action-review-button" onClick={()=>router.push(query('/dashboard/actions',{draft:text(action.id)}))}>Review<ArrowRight size={14}/></Button></article>)}</div>{actions.length>0&&!actions.some(action=>(!actionStatus||action.status===actionStatus)&&(!actionQuery||JSON.stringify(action).toLowerCase().includes(actionQuery.toLowerCase())))&&<div className="empty-state"><h3>No matching actions.</h3><p>Try a different search or status.</p></div>}</ResourceState></Panel>}{tab === 'alerts' && <Panel><PanelTitle title="Priority alerts" description="Acknowledgement and resolution are recorded by the backend"><label className="checkbox-label"><input type="checkbox" checked={closed} onChange={e => setClosed(e.target.checked)} />Include closed</label></PanelTitle><ResourceState resource={alerts} empty={alerts.data !== undefined && !alertRows.length}><div className="live-alert-list">{alertRows.map(alert => <article key={text(alert.id)}><header><h3>{text(alert.title)}</h3><Status value={alert.severity} severity /><Status value={alert.status} /></header><SourceBadge value={alert.source} /><details><summary>Why this alert?</summary><p>{text(alert.why)}</p><p>Due {dateText(alert.due_date)}{alert.status!=='resolved'&&dueNote(alert.due_date,date)?' · '+dueNote(alert.due_date,date):''}</p></details>{amendmentsFor(alert).map(am=><div className="am-alert" key={text(am.id)}><AmendmentSummary action={am} onOpen={()=>router.push(query('/dashboard/actions',{draft:text(am.id)}))}/></div>)}<Citations values={alert.citations} />{canAdmin && <div className="button-row">{['acknowledged','snoozed','resolved'].map(status => <Button key={status} variant="secondary" disabled={m.pending || demo || alert.status === status} onClick={() => void m.run('/api/alerts/' + encodeURIComponent(text(alert.id)),{status,...(status === 'snoozed' ? {snooze_days:7} : {})})}>{status === 'snoozed' ? 'Snooze 7 days' : status === 'acknowledged' ? 'Acknowledge' : 'Resolve'}</Button>)}</div>}</article>)}</div></ResourceState></Panel>}{tab === 'violations' && <Panel><PanelTitle title="Violations" description="Suspected and confirmed breaches with source references" /><ResourceState resource={violations} empty={violations.data !== undefined && !vRows.length}><div className="live-alert-list">{vRows.map(v => <article key={text(v.id)}><header><strong>{text(v.contract_id)} · {text(v.breach_type)}</strong><Status value={v.status} /></header><p>Breached by {text(v.breached_by)}</p><FieldValue value={v.exposure} /><SourceBadge value={v.source} /><CitationChip value={{...record(v.citation),contract_id:v.contract_id,clause_number:v.clause_number ?? record(v.citation).clause_number}} /><a className="text-link" href={query('/viewer',{contract:text(v.contract_id),clause:text(v.clause_number,''),violation:text(v.id)})}>View references →</a></article>)}</div></ResourceState></Panel>}<Sheet open={Boolean(selected)} onOpenChange={open => { if (!open) router.push('/dashboard/actions'); }} title="Action review" description="Inspect the source, edit the draft and approve before taking action.">{selected && <ActionDetail actionId={selected} />}</Sheet></>;
}
function ActionDetail({ actionId }: { actionId:string }) {
 const r = useResource('/api/actions/' + encodeURIComponent(actionId)); const action = record(r.data); const {canAdmin,demo} = useWorkspace();
 const [to,setTo] = useState(''); const [subject,setSubject] = useState(''); const [body,setBody] = useState(''); const [approved,setApproved] = useState(false); const [confirm,setConfirm] = useState(false);
 const [wallClock, setWallClock] = useState(Date.now);
 const dispatching = useRef(false);
 const m = useMutation(); const [result,setResult] = useState<unknown>();
 useEffect(() => { if (r.data !== undefined) { setTo(text(record(r.data).to,'')); setSubject(text(record(r.data).subject,'')); setBody(text(record(r.data).body_md,'')); setApproved(false); setConfirm(false); } },[r.data]);
 useEffect(() => { const timer = setInterval(() => setWallClock(Date.now()), 1000); return () => clearInterval(timer); }, []);
 const operation = deliveryOperation(action.kind);
 const recipientValid = operation !== 'send' || validActionRecipients(to);
 const eligibility = record(action.approval_eligibility);
 const approvalBlocked = eligibility.can_approve === false;
 const security = actionSecurity(action, wallClock);
 const editable = canAdmin && security.canReview;
 const dirty = to !== text(action.to,'') || subject !== text(action.subject,'') || body !== text(action.body_md,'');
 const dispatch = async () => {
  // Recheck the actual wall clock at the click boundary, including a background tab.
  if (dispatching.current || !actionSecurity(action, Date.now()).canExecute || dirty || !confirm || !recipientValid || demo) return;
  dispatching.current = true;
  try { const output = await m.run('/api/actions/' + encodeURIComponent(actionId) + '/' + operation); setResult(output); }
  finally { dispatching.current = false; }
 };
 return <ResourceState resource={r}>{r.data !== undefined && <>
  <div className="workplan-summary"><Status value={action.status} /><SourceBadge value={action.source} /><TraceLink value={action.trace_url} /></div>
  {action.kind === 'amendment' && <><p className="muted-note">Local proposal only. Applying creates a local proposed contract version; counterparty consent and legal effectiveness are not established.</p><AmendmentDetail action={action} /></>}
  <div className="action-editor">
   <label>Recipient<input type="text" className="input" value={to} onChange={e => setTo(e.target.value)} disabled={!editable || m.pending || demo} /></label>
   <label>Subject<input className="input" value={subject} onChange={e => setSubject(e.target.value)} disabled={!editable || m.pending || demo} /></label>
   <label>Letter / amendment<textarea rows={15} value={body} onChange={e => setBody(e.target.value)} disabled={!editable || m.pending || demo} /></label>
  </div>
  {!recipientValid && <p className="form-error" role="alert">{editable ? 'Enter a recipient email address and save before approving this draft.' : 'Cannot send: the recipient must be a valid email address.'}</p>}
  {!operation && action.status === 'approved' && <p className="muted-note">Delivery is unavailable for this action type.</p>}
  <Citations values={action.citations} />
  {action.kind !== 'amendment' && <><h3>Financial counterfactual</h3><SourceBadge value="analysis" /><FieldValue value={action.counterfactual} /></>}
  {action.leverage_notes ? <><h3>Leverage notes</h3><FieldValue value={action.leverage_notes} /></> : null}
  <div className="detail-list">
   <div><span>Approved by</span><strong>{text(action.approved_by)}</strong></div>
   <div><span>Approved at</span><strong>{dateTimeText(action.approved_at)}</strong></div>
   <div><span>Bound tool</span><strong>{text(security.binding.tool, 'Requires fresh approval')}</strong></div>
   <div><span>Approval expires (wall clock)</span><strong>{dateTimeText(security.binding.expires_at)}</strong></div>
   <div><span>Execution state</span><strong>{security.execution}</strong></div>
   <div><span>Payload binding</span><strong>{security.binding.payload_hash ? 'Saved payload hash recorded' : 'Missing'}</strong></div>
  </div>
  <p className="muted-note">Bound sources: {security.sources.length ? security.sources.map(source => text(source.contract_id) + ' · version ' + text(source.version)).join('; ') : 'No source versions recorded.'} The server checks current source versions, payload and prerequisites again before execution.</p>
  {!security.canExecute && <p className="muted-note" role="status">{security.reason}</p>}
  {approvalBlocked && <p className="muted-note" role="status">Before approval: {text(eligibility.reason)}</p>}
  {editable && <>
   <Button variant="secondary" disabled={!dirty || m.pending || demo} onClick={() => void m.run('/api/actions/' + encodeURIComponent(actionId),{to,subject,body_md:body},'PATCH')}>{action.status === 'approved' ? 'Save edits & require fresh review' : 'Save draft'}</Button>
   {action.status === 'approved' && <p className="muted-note">Saving edits invalidates this approval and returns the action to draft. Reviewing again creates a new approval for the saved content and current sources.</p>}
   <label className="checkbox-label"><input type="checkbox" checked={approved} disabled={m.pending || demo} onChange={e => setApproved(e.target.checked)} />I reviewed the source, recipient and saved draft.</label>
   <div className="button-row">
    <Button disabled={!approved || dirty || m.pending || demo || !recipientValid || !operation || approvalBlocked} onClick={() => void m.run('/api/actions/' + encodeURIComponent(actionId) + '/approve')}>{action.status === 'approved' ? 'Review & renew approval' : 'Approve draft'}</Button>
    <Button variant="secondary" disabled={m.pending || demo} onClick={() => void m.run('/api/actions/' + encodeURIComponent(actionId) + '/reject')}>Reject</Button>
   </div>
   {dirty && <p className="muted-note">Save your edits before approval or execution.</p>}
  </>}
  {canAdmin && action.status === 'approved' && operation && <div className="approval-box">
   <label className="checkbox-label"><input type="checkbox" checked={confirm} disabled={!security.canExecute || dirty || m.pending || demo} onChange={e => setConfirm(e.target.checked)} />Confirm {operation === 'apply' ? 'creating a local proposed amendment version; counterparty consent is not established' : 'sending this approved message through Gmail'}.</label>
   <Button disabled={!confirm || !security.canExecute || dirty || m.pending || demo || !recipientValid} onClick={() => void dispatch()}>{operation === 'apply' ? 'Apply local proposal' : 'Send approved message'}</Button>
  </div>}
  {demo && <p className="muted-note">Approvals in preview are local fixtures. Sending and applying require the backend.</p>}
  <MutationFeedback mutation={m} />{result !== undefined && <FieldValue value={result} />}
 </>}</ResourceState>;
}
