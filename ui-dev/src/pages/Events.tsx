import { useState } from "react";
import { api, Any, money, nav } from "../api";
import { useLive } from "../App";
import { Busy, Err, Sev, Status, useApi } from "../components";

const SAMPLE_SUBJECT = "[ODIN-EVENT] PAYMENT_LATE MSA-2026-001";
const SAMPLE_BODY = `EVENT_TYPE: PAYMENT_LATE
OCCURRED_AT: 2026-10-28T10:30:00+05:30
CONTRACT_ID: MSA-2026-001
AMOUNT: INR 3,00,000
DESCRIPTION:
Invoice NIM-2026-09 still unpaid.`;

/** Heimdall's inbox: Gmail events, manual fallback, what-if sandbox, demo feed. */
export default function Events() {
  const { me } = useLive();
  const [evs, reload, err] = useApi<Any[]>("/events");
  const [tpl] = useApi<string>("/email/template");
  const [status] = useApi("/email/status");
  const [subject, setSubject] = useState(SAMPLE_SUBJECT);
  const [body, setBody] = useState(SAMPLE_BODY);
  const [res, setRes] = useState<Any>(null);
  const [wif, setWif] = useState<string | null>(null);
  const [scen, reloadScen] = useApi(wif ? `/whatif/${wif}` : null, [wif]);

  return (
    <div className="grid">
      <section className="card">
        <h3>Live feed — {me.gmail_connected ? `watching ${me.gmail_address}` : "Gmail not connected"}</h3>
        <p className="small">Judges: email <b>{me.gmail_address || "(connect Gmail first)"}</b> with this format. Malformed mails get an auto-reply with the template.</p>
        <pre className="small">{tpl}</pre>
        <div className="row">
          <Busy label="Poll Gmail now" run={() => api.post("/email/poll-now").then((r) => { setRes(r); reload(); })} />
          <Busy label="Demo: play scripted emails" run={() => api.post("/demo/play?delay_seconds=25").then(setRes)} />
        </div>
        {status?.at && <div className="small muted">last poll {status.at} · fetched {status.fetched} {status.error && `· ${status.error}`}</div>}
      </section>
      <section className="card">
        <h3>Send event manually / What-if</h3>
        <input value={subject} onChange={(e) => setSubject(e.target.value)} />
        <textarea rows={9} value={body} onChange={(e) => setBody(e.target.value)} />
        <div className="row">
          <Busy label="Submit real event" run={() => api.post("/events", { subject, body, sender: me.user.email }).then((r) => { setRes(r); reload(); })} />
          <Busy label="Run as what-if (sandbox)" run={() => api.post("/whatif", { subject, body }).then((r) => { setRes(r); setWif(r.scenario_id); })} />
        </div>
        {res && <pre className="small">{JSON.stringify(res, null, 1)}</pre>}
      </section>
      {wif && scen && <section className="card span2">
        <h3>What-if result <Status s={scen.run?.status} /> <button onClick={reloadScen}>refresh</button>
          <button onClick={() => api.del(`/whatif/${wif}`).then(() => setWif(null))}>discard</button></h3>
        <div>Worst case now {money(scen.exposure_base?.worst_case)} → with this event {money(scen.exposure_scenario?.worst_case)}</div>
        {(scen.records.alert ?? []).map((a: Any) => <div key={a.id} className="alert"><Sev s={a.severity} /> {a.title} — {a.why}</div>)}
        {(scen.records.violation ?? []).map((v: Any) => <div key={v.id} className="small">violation: {v.contract_id} §{v.clause_number} {v.breach_type}</div>)}
        {(scen.records.action ?? []).map((a: Any) => <div key={a.id} className="small">action: {a.kind} — {a.subject}</div>)}
        <div className="stream small">{scen.messages.map((m: Any) => <div key={m.id}><b>{m.sender}</b>: {m.summary}</div>)}</div>
      </section>}
      <section className="card span2">
        <h3>Events</h3><Err e={err} />
        <table><thead><tr><th>When</th><th>Type</th><th>Contracts</th><th>Amount</th><th>Status</th><th>Parse</th><th>Detail</th></tr></thead>
          <tbody>{evs?.map((e) => <tr key={e.id}>
            <td>{String(e.occurred_at).slice(0, 16)}</td><td>{e.event_type}</td>
            <td>{e.contract_ids?.map((c: string) => <a key={c} onClick={() => nav("contract", { id: c })}>{c} </a>)}</td>
            <td>{e.amount ? money(e.amount.amount, e.amount.currency) : ""}</td><td><Status s={e.status} /></td>
            <td className="small">{e.parse_method} {e.parse_confidence < 1 && `(${e.parse_confidence})`}</td>
            <td className="small">{e.reject_reason || e.description?.slice(0, 140)}</td></tr>)}</tbody></table>
      </section>
    </div>
  );
}
