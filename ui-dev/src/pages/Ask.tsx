import { useState } from "react";
import { api, Any } from "../api";
import { Cite, Err } from "../components";

export default function Ask() {
  const [q, setQ] = useState("");
  const [log, setLog] = useState<{ q: string; a: Any }[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const go = () => {
    if (!q.trim()) return;
    setBusy(true); setErr("");
    api.post("/ask", { question: q }).then((a) => { setLog([{ q, a }, ...log]); setQ(""); })
      .catch((e) => setErr(e.message)).finally(() => setBusy(false));
  };
  return (
    <div className="card">
      <h3>Ask Odin <span className="small muted">— answers only from contract text, every claim cited (hybrid BM25 + dense retrieval)</span></h3>
      <div className="row">
        <input className="grow" placeholder="e.g. Which contracts can the counterparty terminate on short notice?" value={q}
          onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && go()} />
        <button disabled={busy} onClick={go}>{busy ? "thinking…" : "Ask"}</button>
      </div>
      <Err e={err} />
      {log.map(({ q, a }, i) => (
        <div key={i} className="qa">
          <div className="q">Q: {q}</div>
          <div className={`a ${a.insufficient_evidence ? "warn" : ""}`}>{a.answer}</div>
          <div>{a.citations.map((c: Any, j: number) => <Cite key={j} c={c} />)}</div>
          <details className="small"><summary>{a.passages.length} retrieved passages</summary>
            {a.passages.map((p: Any, j: number) => <div key={j}><b>{p.contract_id} §{p.clause_number}</b> ({p.score}) {p.text.slice(0, 200)}</div>)}
          </details>
        </div>))}
    </div>
  );
}
