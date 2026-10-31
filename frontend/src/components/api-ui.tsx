'use client';
import Link from 'next/link';
import { useState, type ReactNode } from 'react';
import { ExternalLink, LoaderCircle, RefreshCw } from 'lucide-react';
import { apiUrl, dateText, formatMoney, id, list, record, text, viewerLink, type ApiRecord, type Citation } from '@/lib/api';
import { citationLabel } from '@/lib/odin';
import { useWorkspace } from './providers';
import { Badge, Button, EmptyState } from './ui';

export function SourceBadge({ value }: { value: unknown }) {
  const source = text(value,'');
  return <Badge tone={source === 'sourced' ? 'green' : source === 'analysis' ? 'purple' : 'neutral'}>{source === 'sourced' ? 'SOURCED' : source === 'analysis' ? 'ANALYSIS' : 'Source unspecified'}</Badge>;
}
export function Status({ value, severity = false }: { value: unknown; severity?: boolean }) {
  const label = text(value, 'Unknown');
  const rank = ['info','low','medium','high','critical'].indexOf(label.toLowerCase());
  const n = typeof value === 'number' ? value : rank + 1;
  const tone = severity ? n >= 4 ? 'red' : n >= 3 ? 'amber' : n >= 1 ? 'green' : 'neutral' : ['failed','rejected','missed','blocked','confirmed'].includes(label) ? 'red' : ['partial','pending','draft','suspected','unverified','ambiguous','challenged'].includes(label) ? 'amber' : ['done','approved','sent','applied','processed','verified','found','resolved'].includes(label) ? 'green' : 'purple';
  return <Badge tone={tone}>{severity && typeof value === 'number' ? 'Severity ' + value + '/5' : label.replaceAll('_',' ')}</Badge>;
}
export function CitationChip({ value }: { value: unknown }) {
  const c = record(value);
  if (c.source_type && c.source_type !== 'contract') return <details className="citation-chip"><summary>{text(c.contract_id)} · {text(c.source_type)}{c.verified === false ? ' · Unverified' : ''}</summary><p>{text(c.ref)}</p><blockquote style={{whiteSpace:'pre-wrap'}}>{text(c.quote)}</blockquote></details>;
  if (!c.contract_id || !c.clause_number) return <span className="muted-note">No citation supplied</span>;
  return <Link className={'citation-chip ' + (c.verified === false ? 'citation-warning' : '')} href={viewerLink(c as Citation)} aria-label={'Open section ' + text(c.clause_number) + ' of contract ' + text(c.contract_id) + (typeof c.page === 'number' ? ', page ' + c.page : '') + (c.verified === false ? '. Quote not found in contract' : '')} title={c.verified === false ? 'Quote not found in contract' : text(c.quote,'Open reference')}>
    {citationLabel(c)}{typeof c.page === 'number' ? ' · p.' + c.page : ''}{c.verified === false ? ' · Quote not found in contract' : ''}<ExternalLink size={11} />
  </Link>;
}
export function Citations({ values }: { values: unknown }) { return <div className="citation-list">{Array.isArray(values) && values.map((c,i) => <CitationChip key={i} value={c} />)}</div>; }
export function ResourceState({resource,empty,children}:{resource:{loading:boolean;error:string;reload:()=>void;data?:unknown;dataDate?:string;stale?:boolean};empty?:boolean;children:ReactNode}) {
 if(resource.loading&&resource.data===undefined)return <div className="resource-state" role="status"><LoaderCircle size={20} className="spin"/>Loading this view…</div>;
 if(resource.error&&resource.data===undefined)return <div className="resource-state resource-error" role="alert"><strong>Could not load this view</strong><p>{resource.error}</p><Button variant="secondary" onClick={resource.reload}><RefreshCw size={14}/>Try again</Button></div>;
 return <div className="resource-content" aria-busy={resource.loading}>
  {resource.loading&&<span className="resource-update" role="status"><i/>{resource.stale&&resource.dataDate?'Updating · showing '+dateText(resource.dataDate):'Updating'}</span>}
  {resource.error&&<div className="resource-inline-error" role="alert"><span>Update failed. {resource.dataDate?'Showing '+dateText(resource.dataDate)+'. ':''}{resource.error}</span><button onClick={resource.reload}>Retry</button></div>}
  {empty?<EmptyState title="Nothing here yet." description="There are no records in this view."/>:children}
 </div>;
}
export function useMutation() {
  const { request, refresh } = useWorkspace();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  async function run(path: string, body?: unknown, method = 'POST') {
    setPending(true); setError(''); setSuccess('');
    try { const result = await request(path, { method, body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body) }); refresh(); setSuccess('Saved successfully.'); return result ?? { ok: true }; }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Operation failed.'); return undefined; }
    finally { setPending(false); }
  }
  return { run, pending, error, success, clear: () => { setError(''); setSuccess(''); } };
}
export function MutationFeedback({ mutation }: { mutation: { pending: boolean; error: string; success: string } }) { return <>{mutation.error && <p role="alert" className="form-error">{mutation.error}</p>}{mutation.success && <p role="status" className="mutation-success">{mutation.success}</p>}</>; }
export function DownloadLink({ path, children }: { path: string; children: ReactNode }) {
  const { demo } = useWorkspace();
  try { return demo ? <span className="muted-note">Exports require backend</span> : <a className="button button-secondary" href={apiUrl(path)} target="_blank" rel="noreferrer">{children}<ExternalLink size={13} /></a>; }
  catch { return <span className="muted-note">Connect backend for downloads</span>; }
}
export function FieldValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span className="muted-note">Not provided</span>;
  if (typeof value !== 'object') return <>{String(value)}</>;
  if (typeof record(value).amount === 'number' && typeof record(value).currency === 'string') return <>{formatMoney(value)}</>;
  if (Array.isArray(value)) return <>{value.map((item,i) => <div key={i}><FieldValue value={item} /></div>)}</>;
  return <dl className="record-fields">{Object.entries(record(value)).map(([key,val]) => <div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd><FieldValue value={val} /></dd></div>)}</dl>;
}
export function RecordTable({ rows, columns }: { rows: ApiRecord[]; columns: string[] }) {
  return <div className="table-scroll"><table className="data-table"><thead><tr>{columns.map(c => <th key={c}>{c.replaceAll('_',' ')}</th>)}</tr></thead><tbody>{rows.map((row,index) => <tr key={id(row) || index}>{columns.map(c => <td key={c}>{c === 'status' ? <Status value={row[c]} /> : c === 'source' ? <SourceBadge value={row[c]} /> : c.includes('date') || c.endsWith('_at') ? dateText(row[c]) : <FieldValue value={row[c]} />}</td>)}</tr>)}</tbody></table></div>;
}
export function TraceLink({ value }: { value: unknown }) {
  if (typeof value !== 'string' || !/^https?:\/\//.test(value)) return null;
  return <a className="text-link" href={value} target="_blank" rel="noreferrer">Open trace<ExternalLink size={12} /></a>;
}
