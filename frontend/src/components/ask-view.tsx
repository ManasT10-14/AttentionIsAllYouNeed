'use client';
import { useState } from 'react';
import { useWorkspace } from './providers';
import { record, text } from '@/lib/api';
import { Button, PageTitle, Panel } from './ui';
import { Citations, FieldValue, SourceBadge } from './api-ui';
export function AskView() {
 const {request,demo} = useWorkspace(); const [question,setQuestion] = useState(''); const [contracts,setContracts] = useState(''); const [pending,setPending] = useState(false); const [error,setError] = useState(''); const [messages,setMessages] = useState<{question:string;answer:Record<string,unknown>}[]>([]);
 async function submit(e:React.FormEvent) {
  e.preventDefault(); setPending(true);setError('');
  try{const answer=await request('/api/ask',{method:'POST',body:JSON.stringify({question,...(contracts.trim()?{contract_ids:contracts.split(',').map(s=>s.trim()).filter(Boolean)}:{})})});setMessages(m=>[...m,{question,answer:record(answer)}]);setQuestion('');}catch(cause){setError(cause instanceof Error?cause.message:'Could not answer.');}finally{setPending(false);}
 }
 return <><PageTitle eyebrow="ASK ODIN" title="Ask. Inspect the evidence." description="Answers grounded in your selected contracts, with retrieved passages available for review." /><Panel><div className="ask-messages">{!messages.length && <div className="empty-state"><h2>Start with a contract question.</h2><p>For example: Which agreements need renewal notice in the next month?</p></div>}{messages.map((m,i)=><article key={i}><div className="question-bubble">{m.question}</div><div className="answer-bubble"><SourceBadge value="analysis" />{m.answer.insufficient_evidence===true && <p className="form-error">Insufficient verified evidence to answer this question.</p>}<p>{text(m.answer.answer)}</p><Citations values={m.answer.citations} /><details><summary>Retrieved passages</summary><FieldValue value={m.answer.passages} /></details></div></article>)}</div><form className="ask-form" onSubmit={submit}><label>Contract IDs · optional<input className="input" value={contracts} onChange={e=>setContracts(e.target.value)} placeholder="Comma-separated IDs, or leave empty for all" /></label><label>Your question<textarea rows={3} required value={question} onChange={e=>setQuestion(e.target.value)} placeholder="What needs our attention?" /></label><Button disabled={pending || !question.trim() || demo}>{pending?'Finding evidence…':'Ask Odin'}</Button>{error && <p className="form-error" role="alert">{error}</p>}{demo && <p className="muted-note">Connect the backend to ask questions. Preview does not generate answers.</p>}</form></Panel></>;
}
