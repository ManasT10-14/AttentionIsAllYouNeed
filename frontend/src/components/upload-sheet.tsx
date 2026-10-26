'use client';
import { useState } from 'react';
import Link from 'next/link';
import { record, text } from '@/lib/api';
import { Upload } from 'lucide-react';
import { useWorkspace } from './providers';
import { Button, Sheet } from './ui';
import { FieldValue, MutationFeedback, useMutation } from './api-ui';
export function UploadSheet({ open,onOpenChange,company = false }: { open: boolean; onOpenChange: (open:boolean) => void; company?: boolean }) {
 const { canAdmin,demo } = useWorkspace(); const [files,setFiles] = useState<File[]>([]); const [result,setResult] = useState<unknown>(); const m = useMutation();
 async function submit(e: React.FormEvent) {
  e.preventDefault(); const body = new FormData(); files.forEach(file => body.append(company ? 'file' : 'files',file)); setResult(undefined);
  const response = await m.run(company ? '/api/company/context' : '/api/contracts?analyze=true',body); setResult(response);
 }
 return <Sheet open={open} onOpenChange={onOpenChange} title={company ? 'Company context' : 'Upload contracts'} description={company ? 'Upload company context and review the parsed fields.' : 'Upload one or more agreements. The backend extracts clauses and starts the analysis run.'}>{!canAdmin ? <p>Only administrators can upload documents.</p> : <form onSubmit={submit} className="upload-form"><label className="upload-dropzone" style={{cursor:'pointer',padding:'28px 16px',gap:6}}><Upload size={28} /><strong>{company ? 'Choose a context document' : 'Choose contract files'}</strong><span>{company ? '.md, .txt, .pdf or .docx' : '.pdf, .docx or scanned images (.png .jpg .tif) · multiple files supported'}</span> {files.length ? null : <em className="muted-note">Click here to pick files, then press the button below</em>}<input type="file" style={{position:'absolute',width:1,height:1,opacity:0}} accept={company ? '.md,.txt,.pdf,.docx' : '.pdf,.docx,.png,.jpg,.jpeg,.tif,.tiff'} multiple={!company} disabled={m.pending || demo} onChange={e => setFiles(Array.from(e.target.files ?? []))} /></label>{files.map((file,i) => <p key={i}>{file.name} · {(file.size/1024).toFixed(0)} KB</p>)}<Button disabled={!files.length || m.pending || demo}>{m.pending ? 'Uploading…' : company ? 'Upload and review' : 'Upload and analyse'}</Button>{demo && <p className="muted-note">Uploads are available after connecting the backend. Preview never uploads your files.</p>}<MutationFeedback mutation={m} /></form>}{result !== undefined && <section className="upload-result"><h3>{company ? 'Parsed context · review these fields' : 'Upload results and run IDs'}</h3>{!company && Array.isArray(record(result).run_ids) && (record(result).run_ids as unknown[]).filter((id): id is string => typeof id === 'string').map(id => <div className="button-row" key={id}><Link className="button button-primary" href={'/dashboard/agent-review?run=' + encodeURIComponent(id)} onClick={() => onOpenChange(false)}>Watch agent handoffs</Link><Link className="button button-secondary" href={'/dashboard/workflow?run=' + encodeURIComponent(id)} onClick={() => onOpenChange(false)}>Full workflow</Link></div>)}<FieldValue value={result} /></section>}</Sheet>;
}
