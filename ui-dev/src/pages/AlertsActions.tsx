import { useState } from "react";
import { api, Any, money, nav } from "../api";
import { useLive } from "../App";
import { Busy, Cites, Err, Sev, Status, useApi } from "../components";

function Action({ a, admin, reload }: { a: Any; admin: boolean; reload: () => void }) {
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Any>(null);
  const [cf] = useApi(open ? `/actions/${a.id}` : null, [open]);
  return (
    <div className={`action ${a.status}`}>
      <div className="row">
        <span className="tag">{a.kind}</span><b>{a.contract_id}</b> {a.subject}
        <span className="grow" />
        <Status s={a.status} />{a.needs_human_approval && <span className="pill warn">needs approval</span>}
        <span className="muted small">prio {a.priority} · conf {Math.round(a.confidence * 100)}% · due {a.deadline ?? "—"}</span>
        <button className="link" onClick={() => setOpen(!open)}>{open ? "hide" : "open"}</button>
      </div>
      <Cites cs={a.citations} />
      {open && <div className="inner">
        {cf?.counterfactual?.avoided !== undefined && <div className="pill ok">If done: worst case {money(cf.counterfactual.with_action, cf.counterfactual.currency)} vs
          {" "}{money(cf.counterfactual.without_action, cf.counterfactual.currency)} if not → avoids {money(cf.counterfactual.avoided, cf.counterfactual.currency)}</div>}
        <div className="small">To: {a.to}</div>
        {edit ? <>
          <input value={edit.to} onChange={(e) => setEdit({ ...edit, to: e.target.value })} />
          <input value={edit.subject} onChange={(e) => setEdit({ ...edit, subject: e.target.value })} />
          <textarea rows={12} value={edit.body_md} onChange={(e) => setEdit({ ...edit, body_md: e.target.value })} />
          <Busy label="Save" run={() => api.patch(`/actions/${a.id}`, edit).then(() => { setEdit(null); reload(); })} />
        </> : <pre className="letter">{a.body_md}</pre>}
        {a.redlines?.map((r: Any, i: number) => <div key={i} className="diff modified"><b>§{r.clause_number}</b> — {r.reason}
          <div className="before">{r.before}</div><div className="after">{r.after}</div></div>)}
        {a.leverage_notes && <div className="small"><b>Leverage:</b> {a.leverage_notes}</div>}
        {admin && <div className="row">
          {a.status === "draft" && <>
            <Busy label="Approve" run={() => api.post(`/actions/${a.id}/approve`).then(reload)} />
            <Busy label="Reject" run={() => api.post(`/actions/${a.id}/reject`).then(reload)} />
            <button onClick={() => setEdit({ to: a.to, subject: a.subject, body_md: a.body_md })}>Edit</button></>}
          {a.status === "approved" && a.kind !== "amendment" && <Busy label="Send via Gmail" run={() => api.post(`/actions/${a.id}/send`).then(reload)} />}
          {a.status === "approved" && a.kind === "amendment" && <Busy label="Apply → new contract version" run={() => api.post(`/actions/${a.id}/apply`).then(reload)} />}
        </div>}
      </div>}
    </div>
  );
}

/** FR9.5 — prioritized alert stream + drafted notices with clause citations (human approval FR6.3). */
export default function AlertsActions() {
  const { me } = useLive();
  const [closed, setClosed] = useState(false);
  const [alerts, reloadA, e1] = useApi<Any[]>(`/alerts?include_closed=${closed}`, [closed]);
  const [actions, reloadB, e2] = useApi<Any[]>("/actions");
  const [viols] = useApi<Any[]>("/violations");
  const set = (id: string, status: string) => api.post(`/alerts/${id}`, { status }).then(reloadA);
  const admin = me.user.role === "admin" || me.user.role === "super_admin";

  return (
    <div className="grid">
      <section className="card">
        <h3>Alerts <label className="small"><input type="checkbox" checked={closed} onChange={(e) => setClosed(e.target.checked)} /> show closed</label></h3>
        <Err e={e1} />
        {alerts?.map((a) => (
          <div key={a.id} className={`alert ${a.status}`}>
            <Sev s={a.severity} /> <b>{a.contract_id}</b> {a.title} <Status s={a.status} />
            <div className="small muted">Why: {a.why} {a.due_date && `· due ${a.due_date}`}</div>
            <Cites cs={a.citations} />
            {a.violation_id && <button className="link" onClick={() => {
              const v = viols?.find((x) => x.id === a.violation_id);
              if (v) nav("viewer", { contract: v.contract_id, clause: v.clause_number, v: v.version, violation: v.id });
            }}>View violated clause</button>}
            <div className="row small">
              <button onClick={() => set(a.id, "acknowledged")}>ack</button>
              <button onClick={() => set(a.id, "snoozed")}>snooze 7d</button>
              <button onClick={() => set(a.id, "resolved")}>resolve</button>
            </div>
          </div>))}
      </section>
      <section className="card">
        <h3>Drafted actions (Tyr) <a className="small" href="/api/export/actions.csv">CSV</a> · <a className="small" href="/api/export/calendar.ics">.ics deadlines</a></h3>
        <Err e={e2} />
        {admin && <Busy label="Draft daily digest email" run={() => api.post("/digest/draft").then(reloadB)} />}
        {actions?.map((a) => <Action key={a.id} a={a} admin={admin} reload={reloadB} />)}
      </section>
      <section className="card span2">
        <h3>Violations from events</h3>
        <table><thead><tr><th>Contract</th><th>Clause</th><th>Breach</th><th>By</th><th>Exposure</th><th>Status</th><th /></tr></thead>
          <tbody>{viols?.map((v) => <tr key={v.id}><td>{v.contract_id}</td><td>§{v.clause_number}</td><td>{v.breach_type}</td>
            <td>{v.breached_by}</td><td>{v.exposure ? money(v.exposure.amount, v.exposure.currency) : "—"}</td><td><Status s={v.status} /></td>
            <td><button className="link" onClick={() => nav("viewer", { contract: v.contract_id, clause: v.clause_number, v: v.version, violation: v.id })}>View references</button></td></tr>)}</tbody></table>
      </section>
    </div>
  );
}
