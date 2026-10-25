import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Any } from "../api";
import { Status, useApi } from "../components";

/** NFR4 — work plan, budgets, agent transitions, tool audit, citation guard, LangSmith links. */
export default function Observability() {
  const [o] = useApi("/observability");
  const [cal] = useApi("/insights/calibration");
  const [tools] = useApi<Any[]>("/tools");
  const [cp] = useApi<Any[]>("/insights/counterparties");
  const [runId, setRunId] = useState<string | null>(null);
  const [run] = useApi(runId ? `/runs/${runId}` : null, [runId]);
  const [step, setStep] = useState(0);

  return (
    <div className="grid">
      <section className="card span2">
        <h3>Runs</h3>
        <table><thead><tr><th>Started</th><th>Kind</th><th>Status</th><th>Calls</th><th>Tokens</th><th>USD</th><th>Fallbacks</th><th>Trace</th><th /></tr></thead>
          <tbody>{o?.runs.map((r: Any) => <tr key={r.id}>
            <td className="small">{r.started_at?.slice(0, 19)}</td><td>{r.kind}</td><td><Status s={r.status} /></td>
            <td>{r.budget?.agent_calls}</td><td>{(r.budget?.tokens_in ?? 0) + (r.budget?.tokens_out ?? 0)}</td>
            <td>{r.budget?.usd}</td><td>{r.budget?.fallbacks}</td>
            <td>{r.trace_url ? <a href={r.trace_url} target="_blank" rel="noreferrer">LangSmith</a> : "—"}</td>
            <td><button className="link" onClick={() => { setRunId(r.id); setStep(0); }}>replay</button></td></tr>)}</tbody></table>
        {o?.runs.find((r: Any) => r.error) && <div className="err small">{o.runs.find((r: Any) => r.error).error}</div>}
      </section>
      {run && <section className="card span2">
        <h3>Run replay <span className="muted small">{run.id}</span></h3>
        <input type="range" min={0} max={Math.max(0, run.messages.length - 1)} value={step} onChange={(e) => setStep(+e.target.value)} className="grow" />
        <div className="stream">{run.messages.slice(0, step + 1).map((m: Any) => (
          <div key={m.id} className="msg"><b>{m.sender}</b> → {m.receiver} <span className="tag">{m.kind}</span> {m.summary}</div>))}</div>
        <details><summary>{run.tool_calls.length} tool calls (audit)</summary>
          {run.tool_calls.map((t: Any, i: number) => <div key={i} className={`small ${t.ok ? "" : "err"}`}>{t.agent} · {t.tool} [{t.scope}] {t.ms}ms {t.blocked && "BLOCKED"} {t.summary}</div>)}
        </details>
        {run.budget?.per_agent && <table className="mini"><tbody>{Object.entries(run.budget.per_agent).map(([a, v]: [string, Any]) =>
          <tr key={a}><td>{a}</td><td>{v.calls} calls</td><td>{v.tokens} tok</td><td>${v.usd}</td><td>{Math.round(v.latency_ms)} ms</td><td className="small">{JSON.stringify(v.providers)}</td></tr>)}</tbody></table>}
      </section>}
      <section className="card">
        <h3>Citation guard</h3>
        <div>Checked {o?.citation_guard.checked ?? 0} · verified {o?.citation_guard.verified ?? 0} ·
          <b> hallucinated quotes blocked {o?.citation_guard.blocked ?? 0}</b></div>
        <div className="small muted">Stored citations {o?.citation_guard.stored_citations}, unverified {o?.citation_guard.stored_unverified}.
          Blocked tool calls {o?.blocked_tool_calls}.</div>
        <h4>Confidence calibration (Thor)</h4>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={cal?.buckets ?? []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="confidence" /><YAxis domain={[0, 1]} />
            <Tooltip /><Bar dataKey="verified_rate" fill="#2563eb" /></BarChart>
        </ResponsiveContainer>
      </section>
      <section className="card">
        <h3>Counterparty risk</h3>
        <table className="mini"><tbody>{cp?.map((c) => <tr key={c.name}><td>{c.name}</td><td>{c.contracts.join(", ")}</td>
          <td>worst {Math.round(c.worst_case).toLocaleString("en-IN")}</td><td>{c.violations} viol.</td><td>{c.late_payment_events} late</td></tr>)}</tbody></table>
        <h4>Limits & providers</h4><pre className="small">{JSON.stringify({ limits: o?.limits, providers: o?.providers }, null, 1)}</pre>
      </section>
      <section className="card span2">
        <h3>Tool registry (security-suite surface)</h3>
        <table><thead><tr><th>Tool</th><th>Scope</th><th>Side effect</th><th>Approval</th><th>PII</th><th>Agents</th></tr></thead>
          <tbody>{tools?.map((t) => <tr key={t.name}><td>{t.name}</td><td>{t.scope}</td><td>{t.side_effect ? "yes" : ""}</td>
            <td>{t.requires_approval ? "yes" : ""}</td><td>{t.pii ? "yes" : ""}</td><td className="small">{t.allowed_agents.join(", ")}</td></tr>)}</tbody></table>
      </section>
    </div>
  );
}
