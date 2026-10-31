'use client';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { useWorkspace } from './providers';
import { list, record, text } from '@/lib/api';
import { askHistory, askReason, type AskMessage } from '@/lib/ask-conversation';
import { useResource } from '@/lib/use-resource';
import { Badge, Button, PageTitle, Panel } from './ui';
import { ASK_STARTERS } from '@/lib/odin';
import { Citations, FieldValue, SourceBadge } from './api-ui';
const STARTERS = ASK_STARTERS;
export function AskView() {
 const { request, demo } = useWorkspace();
 const available = useResource('/api/contracts');
 const [question, setQuestion] = useState(''); const [contracts, setContracts] = useState<string[]>([]);
 const [pending, setPending] = useState(false); const [elapsed, setElapsed] = useState(0);
 const [error, setError] = useState(''); const [messages, setMessages] = useState<AskMessage[]>([]);
 const active = useRef<AbortController | null>(null);
 useEffect(() => () => active.current?.abort(), []);
 useEffect(() => {
  if (!pending) return;
  const timer = setInterval(() => setElapsed(s => s + 1), 1000);
  return () => clearInterval(timer);
 }, [pending]);
 async function submit(e: React.FormEvent) {
  e.preventDefault(); if (pending || !question.trim()) return;
  const asked = question.trim(); const controller = new AbortController(); active.current = controller;
  setPending(true); setElapsed(0); setError('');
  try {
   const answer = await request('/api/ask', { method: 'POST', signal: controller.signal, body: JSON.stringify({ question: asked, contract_ids: contracts.length ? contracts : undefined, history: askHistory(messages) }) });
   setMessages(m => [...m, { question: asked, answer: record(answer) }]); setQuestion('');
  } catch (cause) {
   setError(controller.signal.aborted ? 'Stopped waiting for this answer. Server processing may still finish.' : cause instanceof Error && cause.name === 'TimeoutError' ? 'The answer took too long. Try selecting an agreement or asking a narrower question.' : cause instanceof Error ? cause.message : 'Could not answer. Please retry.');
  } finally { active.current = null; setPending(false); }
 }
 return <><PageTitle eyebrow="ASK ODIN" title="Ask. Inspect the evidence." description="Ask across your portfolio or select agreements. Follow-up questions use your recent conversation; legal claims require verified clause quotations." /><Panel>
 <div className="ask-messages">{!messages.length && <div className="empty-state"><h2>Start with a contract question.</h2><p>Ask about the portfolio, one agreement, or a specific clause.</p><div className="citation-list">{STARTERS.map(s => <button type="button" key={s} className="citation-chip" disabled={pending} onClick={() => setQuestion(s)}>{s}</button>)}</div></div>}
 {messages.map((m, i) => <article key={i}><div className="question-bubble">{m.question}</div><div className="answer-bubble"><div className="button-row"><SourceBadge value="analysis" />{m.answer.status === 'partial' && <Badge tone="amber">Partially answered</Badge>}</div>
 {askReason(m.answer) && <p className={m.answer.insufficient_evidence ? 'form-error' : 'muted-note'}>{askReason(m.answer)}</p>}
 {m.answer.answer ? <p className="ask-answer-text">{text(m.answer.answer)}</p> : null}<Citations values={m.answer.citations} />
 {record(m.answer.next_step).href==='/dashboard/simulation'&&<Link className="button button-secondary" href="/dashboard/simulation">Open Simulation</Link>}
 {list(m.answer.supporting_claims).length > 0 && <details><summary>Checked calculations and conditions</summary>{list(m.answer.supporting_claims).map((claim,j) => <div key={j}><p>{text(claim.text)}</p><Citations values={claim.citations} /></div>)}</details>}
 {Array.isArray(m.answer.missing) && m.answer.missing.length > 0 && <details className="ask-limitations" open={m.answer.insufficient_evidence === true}><summary>{m.answer.insufficient_evidence ? 'What is needed' : 'Evidence gaps'} ({m.answer.missing.length})</summary><ul>{m.answer.missing.map((gap, j) => <li key={j}>{text(gap)}</li>)}</ul></details>}
 {Array.isArray(m.answer.warnings) && m.answer.warnings.map((warning, j) => <p className="muted-note" key={j}>{text(warning)}</p>)}
 {list(m.answer.sources).length > 0 && <details><summary>Agreement scope ({list(m.answer.sources).length})</summary><div className="citation-list">{list(m.answer.sources).map((s, j) => <span key={j} className="citation-chip">{text(s.title, text(s.contract_id))}</span>)}</div></details>}
 <details><summary>Retrieved evidence ({list(m.answer.passages).length} passages)</summary>{m.answer.resolved_question && m.answer.resolved_question !== m.question ? <p className="muted-note">Search context: {text(m.answer.resolved_question)}</p> : null}<FieldValue value={m.answer.passages} /></details>
 {m.answer.insufficient_evidence === true && <button type="button" className="text-link" disabled={pending} onClick={() => setQuestion(m.question)}>Edit and retry question</button>}</div></article>)}
 </div>
 <form className="ask-form" onSubmit={submit}><label>Agreement scope - optional<select multiple size={Math.min(5, Math.max(2, list(available.data).length))} value={contracts} disabled={pending} onChange={e => setContracts(Array.from(e.target.selectedOptions, o => o.value))}>{list(available.data).map(c => <option key={text(c.id ?? c.contract_id)} value={text(c.id ?? c.contract_id)}>{text(c.title)} ({text(c.id ?? c.contract_id)})</option>)}</select><small>No selection searches all agreements. Hold Ctrl or Command to select several.</small></label>
 {contracts.length > 0 && <button type="button" className="text-link" disabled={pending} onClick={() => setContracts([])}>Clear selection</button>}
 {available.error && <p className="form-error">Agreement names could not be loaded. <button type="button" className="text-link" onClick={available.reload}>Retry</button></p>}
 <label>Your question<textarea rows={3} maxLength={4000} required value={question} disabled={pending} onChange={e => setQuestion(e.target.value)} placeholder="What needs our attention?" /></label>
 <div className="button-row"><Button disabled={pending || !question.trim() || demo}>{pending ? 'Preparing verified answer...' : 'Ask Odin'}</Button>{pending && <Button type="button" variant="secondary" onClick={() => active.current?.abort()}>Stop waiting</Button>}{messages.length > 0 && !pending && <Button type="button" variant="ghost" onClick={() => setMessages([])}>New conversation</Button>}</div>
 {pending && <p role="status" className="muted-note">Working on your question ({elapsed}s). Retrieval and evidence verification can take longer for complex questions.{elapsed >= 30 ? ' Still waiting for the answer service; you can stop waiting above.' : ''}</p>}
 {error && <p className="form-error" role="alert">{error}</p>}{demo && <p className="muted-note">Connect the backend to ask questions. Preview does not generate answers.</p>}
 </form></Panel></>;
}
