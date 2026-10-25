import { useState } from "react";
import { Any } from "../api";
import { Cite, Sev, Status, useApi } from "../components";

const AGENTS: Record<string, string> = { odin: "#6b7280", thor: "#2563eb", norns: "#0891b2", loki: "#16a34a",
  heimdall: "#d97706", tyr: "#7c3aed", synth: "#475569" };

/** FR9.4 — live view of Loki's attacks, Heimdall's verifications and Tyr's rulings. */
export default function Debate({ contractId }: { contractId?: string }) {
  const [filter, setFilter] = useState(contractId ?? "");
  const [d] = useApi(`/debate${filter ? `?contract_id=${encodeURIComponent(filter)}` : ""}`, [filter]);
  const [contracts] = useApi<Any[]>("/contracts");
  const rulings: Record<string, Any> = Object.fromEntries((d?.rulings ?? []).map((r: Any) => [r.finding_id, r]));

  return (
    <div className="grid">
      <section className="card span2 row">
        Contract <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">all</option><option value="cross">cross-contract</option>
          {contracts?.map((c) => <option key={c.contract_id}>{c.contract_id}</option>)}</select>
      </section>
      <section className="card">
        <h3>Findings & debate threads</h3>
        {d?.findings.map((f: Any) => (
          <div key={f.id} className="finding">
            <div><Sev s={f.severity} /> <Status s={f.status} /> <b>{f.contract_id}</b> · {f.kind}</div>
            <div className="bubble loki"><b>Loki:</b> {f.claim}<div className="small muted">{f.attack_path}</div>
              {f.citations.map((c: Any, i: number) => <Cite key={i} c={c} />)}</div>
            {(f.debate ?? []).map((t: Any, i: number) => (
              <div key={i} className={`bubble ${t.by}`}><b>{t.by === "heimdall" ? `Heimdall (${t.verdict})` : `Loki (${t.position})`}:</b>{" "}
                {t.rationale ?? t.argument}</div>))}
            {rulings[f.id] && <div className="bubble tyr"><b>Tyr rules {rulings[f.id].winner}</b> (severity {rulings[f.id].final_severity},
              conf {rulings[f.id].confidence}): {rulings[f.id].rationale}</div>}
          </div>))}
        {d && !d.findings.length && <p className="muted">No findings yet.</p>}
      </section>
      <section className="card">
        <h3>Agent message stream</h3>
        <div className="stream">{[...(d?.messages ?? [])].reverse().map((m: Any) => (
          <div key={m.id} className="msg">
            <span className="agent" style={{ background: AGENTS[m.sender] ?? "#999" }}>{m.sender}</span>
            <span className="muted">→ {m.receiver}</span> <span className="tag">{m.kind}</span>
            <span className="small muted"> {m.ts.slice(11, 19)}</span>
            <div className="small">{m.summary}</div></div>))}</div>
      </section>
    </div>
  );
}
