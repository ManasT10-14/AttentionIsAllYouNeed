'use client';
import { useState } from 'react';
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
 return <Sheet open={open} onOpenChange={onOpenChange} title={company ? 'Company context' : 'Upload contracts'} description={company ? 'Upload company context and review the parsed fields.' : 'Upload one or more agreements. The backend extracts clauses and starts the analysis run.'}>{!canAdmin ? <p>Only administrators can upload documents.</p> : <form onSubmit={submit} className="upload-form"><label className="upload-drop"><Upload size={28} /><strong>{company ? 'Choose a context document' : 'Choose contract files'}</strong><span>{company ? '.md, .txt, .pdf or .docx' : '.pdf or .docx · multiple files supported'}</span><input type="file" accept={company ? '.md,.txt,.pdf,.docx' : '.pdf,.docx'} multiple={!company} disabled={m.pending || demo} onChange={e => setFiles(Array.from(e.target.files ?? []))} /></label>{files.map((file,i) => <p key={i}>{file.name} · {(file.size/1024).toFixed(0)} KB</p>)}<Button disabled={!files.length || m.pending || demo}>{m.pending ? 'Uploading…' : company ? 'Upload and review' : 'Upload and analyse'}</Button>{demo && <p className="muted-note">Uploads are available after connecting the backend. Preview never uploads your files.</p>}<MutationFeedback mutation={m} /></form>}{result !== undefined && <section className="upload-result"><h3>{company ? 'Parsed context · review these fields' : 'Upload results and run IDs'}</h3><FieldValue value={result} /></section>}</Sheet>;
}
