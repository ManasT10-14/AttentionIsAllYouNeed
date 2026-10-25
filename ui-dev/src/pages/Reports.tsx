import { useState } from "react";
import { api, Any } from "../api";
import { Busy, useApi } from "../components";

/** FR8 — per-contract + company risk reports (HTML view, PDF export). References link to the viewer. */
export default function Reports({ params }: { params: URLSearchParams }) {
  const [contracts] = useApi<Any[]>("/contracts");
  const [which, setWhich] = useState(params.get("contract") ?? "company");
  const src = which === "company" ? "/api/reports/company?format=html" : `/api/reports/contract?contract_id=${which}&format=html`;
  const pdf = src.replace("format=html", "format=pdf");
  const [n, setN] = useState(0);
  return (
    <div className="card">
      <div className="row">
        <select value={which} onChange={(e) => setWhich(e.target.value)}>
          <option value="company">Company risk report</option>
          {contracts?.map((c) => <option key={c.contract_id} value={c.contract_id}>{c.contract_id} — {c.title}</option>)}
        </select>
        <a className="btn" href={pdf}>Download PDF</a>
        <Busy label="Regenerate reports" run={() => api.post("/reports/refresh").then(() => setTimeout(() => setN(n + 1), 4000))} />
      </div>
      <iframe key={src + n} title="report" src={src} className="report"
        onLoad={(e) => {   // make reference links open the in-app viewer
          const doc = (e.target as HTMLIFrameElement).contentDocument;
          doc?.querySelectorAll("a[href^='/viewer']").forEach((a) => a.addEventListener("click", (ev) => {
            ev.preventDefault();
            window.location.hash = "/viewer?" + (a.getAttribute("href") || "").split("?")[1];
          }));
        }} />
    </div>
  );
}
