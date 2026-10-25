import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { api, Any, money, nav } from "../api";
import { Err, Sev, Status } from "../components";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

/** "View references": original PDF at the exact page, cited clause highlighted, context on the side. */
export default function Viewer({ params }: { params: URLSearchParams }) {
  const contract = params.get("contract")!;
  const clause = params.get("clause");
  const v = params.get("v");
  const violationId = params.get("violation");
  const [target, setTarget] = useState<Any>(null);
  const [viol, setViol] = useState<Any>(null);
  const [err, setErr] = useState("");
  const [pageNo, setPageNo] = useState(1);
  const [pages, setPages] = useState(0);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [boxes, setBoxes] = useState<number[][]>([]);
  const [scale, setScale] = useState(1.4);
  const doc = useRef<Any>(null);

  useEffect(() => {
    setErr("");
    if (violationId) api.get(`/violations/${violationId}`).then(setViol).catch(() => setViol(null));
    if (clause) {
      api.get(`/citation/resolve?contract=${encodeURIComponent(contract)}&clause=${encodeURIComponent(clause)}${v ? `&v=${v}` : ""}`)
        .then((t) => { setTarget(t); setPageNo(t.page); }).catch((e) => setErr(e.message));
    } else {
      api.get(`/contracts/${contract}`).then((c) => setTarget({ version: v ? +v : c.version, bboxes: [], contract_id: contract,
        pdf_url: `/api/contracts/${contract}/versions/${v || c.version}/pdf` })).catch((e) => setErr(e.message));
    }
  }, [contract, clause, v, violationId]);

  useEffect(() => {
    if (!target) return;
    let cancelled = false;
    pdfjs.getDocument({ url: target.pdf_url, withCredentials: true }).promise.then((d) => {
      if (cancelled) return;
      doc.current = d;
      setPages(d.numPages);
      setPageNo((p) => Math.min(Math.max(p, 1), d.numPages));
      render(target.page || 1);
    }).catch((e) => setErr(String(e)));
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);

  useEffect(() => { if (doc.current) render(pageNo); /* eslint-disable-next-line */ }, [pageNo, scale]);

  async function render(n: number) {
    const page = await doc.current.getPage(n);
    const vp = page.getViewport({ scale });
    const c = canvas.current!;
    c.width = vp.width;
    c.height = vp.height;
    await page.render({ canvasContext: c.getContext("2d")!, viewport: vp }).promise;
    setBoxes((target?.bboxes || []).filter((b: number[]) => b[0] === n));
    requestAnimationFrame(() => document.querySelector(".hl")?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }

  return (
    <div className="viewer">
      <div className="pdfpane">
        <div className="row">
          <button onClick={() => window.history.back()}>← Back</button>
          <b>{contract}</b> v{target?.version} {clause && <>· §{clause}</>}
          <button disabled={pageNo <= 1} onClick={() => setPageNo(pageNo - 1)}>‹</button>
          <span>page {pageNo}/{pages}</span>
          <button disabled={pageNo >= pages} onClick={() => setPageNo(pageNo + 1)}>›</button>
          <button onClick={() => setScale(scale + 0.2)}>+</button><button onClick={() => setScale(Math.max(0.6, scale - 0.2))}>−</button>
          <a href={target?.pdf_url} target="_blank" rel="noreferrer">open PDF</a>
        </div>
        <Err e={err} />
        <div className="pdfwrap">
          <canvas ref={canvas} />
          {boxes.map((b, i) => (
            <div key={i} className="hl" style={{ left: b[1] * scale - 2, top: b[2] * scale - 2,
              width: (b[3] - b[1]) * scale + 4, height: (b[4] - b[2]) * scale + 4 }} />))}
        </div>
      </div>
      <aside className="side">
        {target?.text && <div className="card"><h4>Cited clause §{target.number} <span className="tag">{target.clause_type}</span></h4>
          <span className="src sourced">SOURCED</span><p className="small">{target.text}</p></div>}
        {viol && <div className="card">
          <h4>Violation <Status s={viol.status} /></h4>
          <div><b>{viol.breach_type}</b> · breached by {viol.breached_by} · exposure {viol.exposure ? money(viol.exposure.amount, viol.exposure.currency) : "—"}</div>
          <p className="small">{viol.explanation}</p>
          {viol.event && <div className="small"><b>Triggering event</b>: {viol.event.event_type} on {String(viol.event.occurred_at).slice(0, 10)}
            <div className="muted">{viol.event.description}</div></div>}
          {viol.ruling?.rationale && <div className="small"><b>Tyr's ruling</b>: {viol.ruling.rationale}</div>}
          {viol.actions?.map((a: Any) => <div key={a.id} className="small"><Sev s={a.kind} /> {a.subject}
            <button className="link" onClick={() => nav("actions")}>open</button></div>)}
        </div>}
      </aside>
    </div>
  );
}
