import { useEffect, useMemo, useRef, useState } from "react";
import { api, Any, money, nav } from "../api";
import { useLive } from "../App";
import { Cites, Sev, Status, useApi } from "../components";

const addDays = (iso: string, n: number) => {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
};

function Gauge({ expected, worst, ccy }: { expected: number; worst: number; ccy: string }) {
  const max = Math.max(worst, 1) * 1.15;
  const arc = (v: number) => {
    const a = Math.PI * (1 - Math.min(v / max, 1));
    return `${100 + 80 * Math.cos(a)},${100 - 80 * Math.sin(a)}`;
  };
  return (
    <svg viewBox="0 0 200 120" className="gauge" role="img" aria-label="Financial exposure gauge">
      <path d="M20,100 A80,80 0 0 1 180,100" className="g-bg" />
      <path d={`M20,100 A80,80 0 0 1 ${arc(worst)}`} className="g-worst" />
      <path d={`M20,100 A80,80 0 0 1 ${arc(expected)}`} className="g-exp" />
      <text x="100" y="88" textAnchor="middle" className="g-big">{money(worst, ccy)}</text>
      <text x="100" y="106" textAnchor="middle" className="g-small">worst case · expected {money(expected, ccy)}</text>
    </svg>
  );
}

function Heatmap({ cells }: { cells: Any[] }) {
  const [by, setBy] = useState<"contract_id" | "clause_type">("contract_id");
  const months = useMemo(() => [...new Set(cells.map((c) => c.month))].sort().slice(0, 14), [cells]);
  const rows = useMemo(() => [...new Set(cells.map((c) => c[by]))].sort(), [cells, by]);
  const val = (r: string, m: string) => cells.filter((c) => c[by] === r && c.month === m).reduce((s, c) => s + c.amount, 0);
  const max = Math.max(1, ...rows.flatMap((r) => months.map((m) => val(r, m))));
  if (!cells.length) return <p className="muted">No exposure yet — run an analysis.</p>;
  return (
    <>
      <div className="row">Rows by <select value={by} onChange={(e) => setBy(e.target.value as Any)}>
        <option value="contract_id">contract</option><option value="clause_type">clause type</option></select></div>
      <div className="scroll"><table className="heat">
        <thead><tr><th />{months.map((m) => <th key={m}>{m}</th>)}</tr></thead>
        <tbody>{rows.map((r) => <tr key={r}><th>{r}</th>{months.map((m) => {
          const v = val(r, m);
          return <td key={m} title={money(v)} style={{ background: v ? `rgba(220,38,38,${0.12 + 0.8 * v / max})` : undefined }}>
            {v ? `${Math.round(v / 1000)}k` : ""}</td>;
        })}</tr>)}</tbody>
      </table></div>
    </>
  );
}

export default function Overview() {
  const { me, refreshMe } = useLive();
  const base = String(me.company.sim_now ?? new Date().toISOString().slice(0, 10));
  const [asOf, setAsOf] = useState(base);
  const [offset, setOffset] = useState(0);
  useEffect(() => { setAsOf(base); setOffset(0); }, [base]);
  const [d] = useApi(`/dashboard?as_of=${asOf}`);
  const [runs] = useApi<Any[]>("/runs?limit=10");
  const timer = useRef<number>();
  const latest = runs?.find((r) => r.kind === "analysis");

  const slide = (n: number) => {
    setOffset(n);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setAsOf(addDays(base, n)), 120);
  };
  const commit = () => api.post("/clock", { sim_now: asOf }).then(refreshMe);

  return (
    <div className="grid">
      <section className="card span2">
        <h3>Simulated clock</h3>
        <div className="row">
          <input type="range" min={-60} max={365} value={offset} onChange={(e) => slide(+e.target.value)}
            onMouseUp={commit} onTouchEnd={commit} className="grow" aria-label="Time slider" />
          <b>{asOf}</b> <span className="muted">({offset >= 0 ? "+" : ""}{offset} days)</span>
          <button onClick={() => api.post("/clock", { days: 7 }).then(refreshMe)}>+1 week</button>
          <button onClick={() => api.post("/clock", { sim_now: new Date().toISOString().slice(0, 10) }).then(refreshMe)}>Reset to today</button>
        </div>
      </section>

      <section className="card">
        <h3>Financial exposure <span className="src analysis">ANALYSIS</span></h3>
        {d && <Gauge expected={d.exposure.expected} worst={d.exposure.worst_case} ccy={d.exposure.currency} />}
        <table className="mini">{d?.exposure.contracts.map((c: Any) => (
          <tr key={c.contract_id}><td><a onClick={() => nav("contract", { id: c.contract_id })}>{c.contract_id}</a></td>
            <td>{money(c.expected, c.currency)}</td><td><b>{money(c.worst_case, c.currency)}</b></td>
            <td className="muted">health {d.health[c.contract_id] ?? "—"}</td></tr>))}</table>
        <p className="muted small">{d?.exposure.note}</p>
      </section>

      <section className="card">
        <h3>Work plan {latest && <Status s={latest.status} />}</h3>
        {!latest && <p className="muted">No analysis yet. Upload contracts on the Contracts tab or use Demo seed.</p>}
        {latest?.workplan?.workstreams?.map((w: Any) => (
          <div key={w.id} className="ws"><Status s={w.status} /> <b>{w.contract_id}</b>
            <span className="muted"> evidence {w.evidence_score}</span>
            {w.reason && <div className="small muted">{w.reason}</div>}</div>))}
        {latest && <div className="small muted">calls {latest.budget?.agent_calls ?? 0} · tokens {(latest.budget?.tokens_in ?? 0) + (latest.budget?.tokens_out ?? 0)} · ${latest.budget?.usd ?? 0}</div>}
      </section>

      <section className="card span2">
        <h3>Risk heatmap (contract / clause type × month)</h3>
        <Heatmap cells={d?.heatmap.cells ?? []} />
      </section>

      <section className="card span2">
        <h3>Top alerts at {asOf}</h3>
        {d?.alerts.slice(0, 10).map((a: Any) => (
          <div key={a.id} className="alert"><Sev s={a.severity} /> <b>{a.contract_id}</b> {a.title}
            <div className="small muted">{a.why}</div><Cites cs={a.citations} /></div>))}
        {d && !d.alerts.length && <p className="muted">No alerts.</p>}
      </section>
    </div>
  );
}
