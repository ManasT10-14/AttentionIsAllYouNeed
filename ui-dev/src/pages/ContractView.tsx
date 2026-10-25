import { useState } from "react";
import { Any, money, nav } from "../api";
import { Cite, Err, Sev, Src, Status, useApi } from "../components";

function fieldRows(x: Any): [string, Any][] {
  if (!x) return [];
  const out: [string, Any][] = [];
  for (const k of ["term", "renewal", "liability_cap", "governing_law"]) if (x[k]) out.push([k, x[k]]);
  for (const k of ["payments", "obligations", "penalties", "compliance", "termination"])
    (x[k] || []).forEach((f: Any, i: number) => out.push([`${k}[${i}]`, f]));
  return out;
}

const valueOf = (f: Any) => {
  const skip = new Set(["confidence", "citation", "status", "note", "source"]);
  return Object.entries(f).filter(([k, v]) => !skip.has(k) && v !== null && v !== "" && !(Array.isArray(v) && !v.length))
    .map(([k, v]) => `${k}: ${typeof v === "object" ? (v as Any).amount !== undefined ? money((v as Any).amount, (v as Any).currency) : JSON.stringify(v) : v}`)
    .join(" · ");
};

export default function ContractView({ id }: { id: string }) {
  const [c, , err] = useApi(`/contracts/${id}`);
  const [tl] = useApi(`/timeline?contract_id=${id}`);
  const [fs] = useApi<Any[]>(`/findings?contract_id=${id}`);
  const [diff, setDiff] = useState<[number, number] | null>(null);
  const [d] = useApi(diff ? `/contracts/${id}/diff?from=${diff[0]}&to=${diff[1]}` : null, [diff]);
  const [lin, setLin] = useState<string | null>(null);
  const [lineage] = useApi(lin ? `/contracts/${id}/lineage/${encodeURIComponent(lin)}` : null, [lin]);
  if (!c) return <Err e={err} />;
  const t = tl?.contracts?.[0];

  return (
    <div className="grid">
      <section className="card span2">
        <h2>{c.title} <span className="muted">{id} · v{c.version} · {c.type}</span></h2>
        <div className="small">{c.meta.parties?.map((p: Any) => `${p.name} (${p.role})`).join(" · ")} · law: {c.meta.governing_law}
          · health <b>{c.health?.score ?? "—"}</b> {c.health?.breakdown && <span className="muted">{JSON.stringify(c.health.breakdown)}</span>}</div>
        <div className="row">
          <button onClick={() => nav("viewer", { contract: id, v: c.version })}>Open document</button>
          <button onClick={() => nav("debate", { contract: id })}>Agent debate</button>
          <button onClick={() => nav("reports", { contract: id })}>Report</button>
          {c.versions.length > 1 && c.versions.slice(1).map((v: Any) => (
            <button key={v.version} onClick={() => setDiff([v.version - 1, v.version])}>Diff v{v.version - 1}→v{v.version}</button>))}
        </div>
      </section>

      {d && <section className="card span2"><h3>Clause diff v{d.from_version} → v{d.to_version}</h3>
        {d.changes.map((ch: Any, i: number) => (
          <div key={i} className={`diff ${ch.change}`}><b>{ch.change}</b> §{ch.number}{ch.old_number ? ` (was ${ch.old_number})` : ""}
            {ch.before && <div className="before">{ch.before}</div>}{ch.after && <div className="after">{ch.after}</div>}</div>))}
        {!d.changes.length && <p className="muted">No clause changes.</p>}</section>}

      <section className="card span2">
        <h3>Extraction (Thor) <Src k="sourced" /></h3>
        {!c.extraction && <p className="muted">Not extracted yet.</p>}
        <table>
          <thead><tr><th>Field</th><th>Value</th><th>Conf.</th><th>Status</th><th>Citation</th></tr></thead>
          <tbody>{fieldRows(c.extraction).map(([k, f]) => (
            <tr key={k} className={f.status !== "found" ? "flagged" : ""}>
              <td>{k}</td><td className="small">{valueOf(f)}{f.note && <div className="muted">{f.note}</div>}</td>
              <td>{(f.confidence * 100).toFixed(0)}%</td><td><Status s={f.status} /></td>
              <td>{f.citation ? <Cite c={f.citation} /> : "—"}</td></tr>))}</tbody>
        </table>
        {c.extraction?.flags?.length > 0 && <>
          <h4>Ambiguity flags</h4>
          {c.extraction.flags.map((fl: Any, i: number) => (
            <div key={i} className="alert"><Status s={fl.kind} /> §{fl.clause_number} {fl.note}
              {fl.related_clauses?.length > 0 && <span className="muted"> (vs §{fl.related_clauses.join(", §")})</span>}</div>))}
        </>}
      </section>

      <section className="card">
        <h3>Timeline (Norns) <Src k="analysis" /></h3>
        {t && <div className="small">Term ends <b>{t.term_end ?? "?"}</b> · notice deadline <b>{t.notice_deadline ?? "—"}</b>
          · worst case <b>{money(t.exposure.worst_case, t.exposure.currency)}</b></div>}
        <div className="scroll tall"><table className="mini">{t?.entries.map((e: Any) => (
          <tr key={e.id} className={e.status}><td>{e.date}</td><td><Status s={e.status} /></td><td>{e.title}</td>
            <td>{e.amount ? money(e.amount.amount, e.amount.currency) : ""}</td><td>{e.citation && <Cite c={e.citation} />}</td></tr>))}</table></div>
        {t?.exposure.assumptions?.map((a: string, i: number) => <div key={i} className="small muted">assumes: {a}</div>)}
      </section>

      <section className="card">
        <h3>Risks (Loki ⇄ Heimdall ⇄ Tyr) <Src k="analysis" /></h3>
        {fs?.filter((f) => f.status !== "withdrawn").map((f) => (
          <div key={f.id} className="finding"><Sev s={f.severity} /> <Status s={f.status} /> <b>{f.kind}</b> — {f.claim}
            <div className="small muted">p={f.likelihood} · {f.attack_path}</div>
            {f.citations.map((ci: Any, i: number) => <Cite key={i} c={ci} />)}</div>))}
      </section>

      <section className="card span2">
        <h3>Clauses (current version)</h3>
        {lineage && <div className="card inner"><b>History of §{lin}</b>
          {lineage.versions.map((v: Any) => <div key={v.version} className="small"><b>v{v.version}</b>: {v.text}</div>)}
          {lineage.findings.map((f: Any) => <div key={f.id} className="small muted">finding ({f.status}): {f.claim}</div>)}</div>}
        {c.clauses.map((cl: Any) => (
          <div key={cl.id} className="clause">
            <a onClick={() => nav("viewer", { contract: id, clause: cl.number, v: cl.version })}>§{cl.number}</a>
            <span className="tag">{cl.clause_type}</span> <span className="muted small">p.{cl.page}</span>
            <button className="link" onClick={() => setLin(cl.number)}>history</button>
            <div className="small">{cl.text}</div></div>))}
      </section>
    </div>
  );
}
