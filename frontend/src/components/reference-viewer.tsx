'use client';
import { useEffect,useRef,useState } from 'react';
import { useSearchParams } from 'next/navigation';
import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist';
import { useResource } from '@/lib/use-resource';
import { apiUrl, query, record, text, type CitationResolution } from '@/lib/api';
import { Button, PageTitle, Panel, PanelTitle } from './ui';
import { DownloadLink, FieldValue, ResourceState, SourceBadge } from './api-ui';
export function ReferenceViewer() {
 const params = useSearchParams(); const contract = params.get('contract') ?? ''; const clause = params.get('clause') ?? ''; const version = params.get('v') ?? ''; const violation = params.get('violation') ?? '';
 const r = useResource<CitationResolution>(contract && clause ? query('/api/citation/resolve',{contract,clause,v:version || undefined}) : null);
 const v = useResource(violation ? '/api/violations/' + encodeURIComponent(violation) : null);
 const [doc,setDoc] = useState<PDFDocumentProxy | null>(null); const [pdfError,setPdfError] = useState(''); const [pdfLoading,setPdfLoading] = useState(false); const [page,setPage] = useState(1); const [scale,setScale] = useState(1.15); const [dimensions,setDimensions] = useState({width:0,height:0}); const canvas = useRef<HTMLCanvasElement>(null); const wrapper = useRef<HTMLDivElement>(null);
 const resolved = r.data; const vNumber = version || text(resolved?.version,'1');
 useEffect(() => {
  if (!resolved || !contract) return;
  let active = true; let document: PDFDocumentProxy | undefined; let destroy: (() => void) | undefined;
  setDoc(null); setPdfError(''); setPdfLoading(true); setPage(resolved.page || 1);
  void (async () => {
   try {
    const pdfjs = await import('pdfjs-dist');
    pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs',import.meta.url).toString();
    const fallback = apiUrl('/api/contracts/' + encodeURIComponent(contract) + '/versions/' + encodeURIComponent(vNumber) + '/pdf');
    const pdfUrl = new URL(resolved.pdf_url || fallback, new URL(fallback,window.location.origin));
    if (pdfUrl.origin !== new URL(fallback,window.location.origin).origin) throw new Error('PDF must be served from the configured backend origin.');
    const task = pdfjs.getDocument({url:pdfUrl.toString(),withCredentials:true});
    destroy = () => { void task.destroy(); };
    document = await task.promise;
    if (active) setDoc(document); else destroy?.();
   } catch (error) { if (active) setPdfError(error instanceof Error ? error.message : 'PDF could not be opened.'); }
   finally { if (active) setPdfLoading(false); }
  })();
  return () => { active=false; destroy?.(); };
 },[resolved,contract,vNumber]);
 useEffect(() => {
  if (!doc || !canvas.current) return;
  let active = true; let render:RenderTask | undefined;
  void (async () => { try {
   const pdfPage = await doc.getPage(page); if(!active || !canvas.current) return;
   const viewport = pdfPage.getViewport({scale}); const context = canvas.current.getContext('2d'); if(!context) throw new Error('Canvas is unavailable.');
   const pixelRatio = window.devicePixelRatio || 1; canvas.current.width = Math.floor(viewport.width*pixelRatio); canvas.current.height = Math.floor(viewport.height*pixelRatio);
   setDimensions({width:viewport.width,height:viewport.height});
   render = pdfPage.render({canvas:canvas.current,canvasContext:context,viewport,transform:pixelRatio !== 1 ? [pixelRatio,0,0,pixelRatio,0,0] : undefined}); await render.promise;
   if(active) wrapper.current?.querySelector('.pdf-highlight')?.scrollIntoView({block:'center',behavior:'instant'});
  } catch(error) { if(active && !(error instanceof Error && error.name === 'RenderingCancelledException')) setPdfError(error instanceof Error ? error.message : 'Page render failed.'); } })();
  return () => {active=false;render?.cancel();};
 },[doc,page,scale]);
 if(!contract || !clause) return <Panel><h2>Select a clause reference.</h2><p>Open this viewer from a citation chip on a finding, action or timeline entry.</p></Panel>;
 return <><PageTitle eyebrow="REFERENCE VIEWER" title={'The source behind ' + (/^\d/.test(clause) ? '§' + clause : /^[A-Z]$/.test(clause) ? 'Section ' + clause : clause)} description={contract + ' · version ' + vNumber}>{contract && <DownloadLink path={'/api/contracts/' + encodeURIComponent(contract) + '/versions/' + encodeURIComponent(vNumber) + '/original'}>Download original</DownloadLink>}</PageTitle><ResourceState resource={r}><div className="reference-layout"><Panel className="pdf-panel"><div className="pdf-controls"><Button variant="secondary" disabled={!doc || page<=1} onClick={() => setPage(p=>p-1)}>Previous</Button><span>Page {page} / {doc?.numPages ?? '—'}</span><Button variant="secondary" disabled={!doc || page>=(doc?.numPages ?? 0)} onClick={() => setPage(p=>p+1)}>Next</Button><label>Zoom<select className="compact-select" value={scale} onChange={e=>setScale(Number(e.target.value))}>{[.75,1,1.15,1.5,2].map(s=><option value={s} key={s}>{Math.round(s*100)}%</option>)}</select></label></div>{pdfLoading && <p role="status">Loading original PDF…</p>}{pdfError && <p className="form-error" role="alert">{pdfError}</p>}<div ref={wrapper} className="pdf-scroll"><div className="pdf-page" style={{width:dimensions.width || undefined,height:dimensions.height || undefined}}><canvas ref={canvas} style={{width:dimensions.width,height:dimensions.height}} />{(resolved?.bboxes ?? []).filter(b=>b[0]===page).map((b,i)=><div className="pdf-highlight" key={i} title="Cited clause" style={{left:b[1]*scale,top:b[2]*scale,width:(b[3]-b[1])*scale,height:(b[4]-b[2])*scale}} />)}</div></div></Panel><aside><Panel><PanelTitle title="Cited clause" /><SourceBadge value="sourced" />{resolved?.verified === false && <p className="form-error">Quote not found in contract</p>}<blockquote className="source-quote">{resolved?.text}</blockquote>{resolved?.clause_type ? <p>{text(resolved.clause_type)}</p> : null}</Panel>{violation && <Panel><PanelTitle title="Violation context" /><SourceBadge value="analysis" /><ResourceState resource={v}><FieldValue value={v.data} /></ResourceState></Panel>}</aside></div></ResourceState></>;
}
