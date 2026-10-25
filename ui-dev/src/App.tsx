import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, Any, nav, route } from "./api";
import Overview from "./pages/Overview";
import Contracts from "./pages/Contracts";
import ContractView from "./pages/ContractView";
import Viewer from "./pages/Viewer";
import GraphView from "./pages/GraphView";
import Debate from "./pages/Debate";
import AlertsActions from "./pages/AlertsActions";
import Events from "./pages/Events";
import Ask from "./pages/Ask";
import Reports from "./pages/Reports";
import Observability from "./pages/Observability";

type Live = { version: number; last: Any[]; me: Any; refreshMe: () => void };
const LiveCtx = createContext<Live>({ version: 0, last: [], me: null, refreshMe: () => {} });
export const useLive = () => useContext(LiveCtx);

const PAGES: [string, string][] = [
  ["overview", "Overview"], ["contracts", "Contracts"], ["graph", "Graph"], ["debate", "Agent debate"],
  ["actions", "Alerts & actions"], ["events", "Events / inbox"], ["ask", "Ask Odin"], ["reports", "Reports"],
  ["observability", "Observability"],
];

function Login({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState("demo@acme.example");
  const [err, setErr] = useState("");
  return (
    <div className="login">
      <h1>RAGNAROK · Odin</h1>
      <p>Multi-agent contract intelligence. Sign in with your company Google account — the same inbox is watched by
        Heimdall for live events.</p>
      <a className="btn primary" href="/api/auth/google/login">Sign in with Google</a>
      <div className="card">
        <b>Dev login</b> (no Google — local demo only)
        <div className="row">
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
          <button onClick={() => api.post("/auth/dev-login", { email, name: "Acme Analytics Pvt Ltd" })
            .then(onDone).catch((e) => setErr(e.message))}>Enter</button>
        </div>
        {err && <div className="err">{err}</div>}
      </div>
    </div>
  );
}

export default function App() {
  const [me, setMe] = useState<Any>(undefined);
  const [r, setR] = useState(route());
  const [version, setVersion] = useState(0);
  const [last, setLast] = useState<Any[]>([]);
  const bump = useRef<number | undefined>();

  const refreshMe = useCallback(() => { api.get("/auth/me").then(setMe).catch(() => setMe(null)); }, []);
  useEffect(refreshMe, [refreshMe]);
  useEffect(() => {
    const f = () => setR(route());
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  useEffect(() => {
    if (!me) return;
    const es = new EventSource("/api/stream", { withCredentials: true });
    es.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      setLast((l) => [msg, ...l].slice(0, 200));
      window.clearTimeout(bump.current);                 // coalesce bursts → one refetch
      bump.current = window.setTimeout(() => setVersion((v) => v + 1), 600);
    };
    return () => es.close();
  }, [me]);

  if (me === undefined) return <div className="pad">Loading…</div>;
  if (me === null) return <Login onDone={refreshMe} />;

  const page = r.page;
  return (
    <LiveCtx.Provider value={{ version, last, me, refreshMe }}>
      <header>
        <b>ᛟ Odin</b>
        <span className="muted">{me.company.name || me.user.email}</span>
        {me.gmail_connected
          ? <span className="pill ok">Heimdall listening on {me.gmail_address}</span>
          : <a className="pill warn" href="/api/auth/google/login"
              title={me.google_configured ? "Connect the company Gmail inbox to this account" : "GOOGLE_CLIENT_ID not configured"}>
              Connect Gmail</a>}
        <span className="pill">sim clock {String(me.company.sim_now ?? "today")}</span>
        <span className="grow" />
        <span className="muted">{me.user.email} · {me.user.role}</span>
        <button onClick={() => api.post("/auth/logout").then(() => setMe(null))}>Log out</button>
      </header>
      <nav>
        {PAGES.map(([k, label]) => (
          <a key={k} className={page === k ? "active" : ""} onClick={() => nav(k)}>{label}</a>
        ))}
      </nav>
      <main>
        {page === "overview" && <Overview />}
        {page === "contracts" && <Contracts />}
        {page === "contract" && <ContractView id={r.params.get("id")!} />}
        {page === "viewer" && <Viewer params={r.params} />}
        {page === "graph" && <GraphView />}
        {page === "debate" && <Debate contractId={r.params.get("contract") || undefined} />}
        {page === "actions" && <AlertsActions />}
        {page === "events" && <Events />}
        {page === "ask" && <Ask />}
        {page === "reports" && <Reports params={r.params} />}
        {page === "observability" && <Observability />}
      </main>
    </LiveCtx.Provider>
  );
}
