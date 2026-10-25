import { useState } from "react";
import { api, Any, nav } from "../api";
import { Busy, Err, Status, useApi } from "../components";

export default function Contracts() {
  const [list, reload, err] = useApi<Any[]>("/contracts");
  const [msg, setMsg] = useState<Any>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [ctxFile, setCtxFile] = useState<File | null>(null);

  return (
    <div className="grid">
      <section className="card">
        <h3>1 · Company context</h3>
        <p className="small muted">Upload the company intro / context document (spec §3.2: COMPANY NAME, BASE CURRENCY,
          APPROVAL THRESHOLD, …).</p>
        <input type="file" accept=".md,.txt,.pdf,.docx" onChange={(e) => setCtxFile(e.target.files?.[0] ?? null)} />
        <Busy label="Upload context" run={() => api.upload("/company/context", [ctxFile!], "file").then(setMsg)} />
      </section>
      <section className="card">
        <h3>2 · Contracts (new or updated versions)</h3>
        <p className="small muted">PDF or DOCX with a cover block and numbered clauses (spec §3.1). Re-uploading a
          CONTRACT ID creates a new version → Odin diffs it, re-extracts only changed clauses and proposes amendments.</p>
        <input type="file" multiple accept=".pdf,.docx" onChange={(e) => setFiles([...(e.target.files ?? [])])} />
        <Busy label={`Upload ${files.length || ""} & analyse`} run={() => api.upload("/contracts", files).then((r) => { setMsg(r); reload(); })} />
        <hr />
        <Busy label="Demo: seed sample contracts" run={() => api.post("/demo/seed").then((r) => { setMsg(r); reload(); })} />{" "}
        <Busy label="Re-run full analysis" run={() => api.post("/runs/analysis", { force: true }).then(setMsg)} />
      </section>
      {msg && <section className="card span2"><pre className="small">{JSON.stringify(msg, null, 1)}</pre></section>}
      <section className="card span2">
        <h3>Contracts</h3><Err e={err} />
        <table>
          <thead><tr><th>ID</th><th>Title</th><th>Type</th><th>Parties</th><th>v</th><th>Health</th><th>Status</th><th>Parse warnings</th></tr></thead>
          <tbody>{list?.map((c) => (
            <tr key={c.contract_id}>
              <td><a onClick={() => nav("contract", { id: c.contract_id })}>{c.contract_id}</a></td>
              <td>{c.title}</td><td>{c.type}</td>
              <td className="small">{c.parties.map((p: Any) => p.name).join(" · ")}</td>
              <td>{c.version}</td><td><b>{c.health?.score ?? "—"}</b></td>
              <td><Status s={c.analysed ? "analysed" : c.status} /></td>
              <td className="small warn">{c.warnings?.join(" ")}</td>
            </tr>))}</tbody>
        </table>
      </section>
    </div>
  );
}
