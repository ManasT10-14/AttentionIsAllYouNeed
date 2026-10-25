import { useEffect, useState } from "react";
import { api, Any, nav } from "./api";
import { useLive } from "./App";

/** Fetch + refetch whenever the live stream says something changed. */
export function useApi<T = Any>(path: string | null, deps: unknown[] = []): [T | undefined, () => void, string] {
  const { version } = useLive();
  const [data, setData] = useState<T>();
  const [err, setErr] = useState("");
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!path) return;
    let alive = true;
    api.get(path).then((d) => { if (alive) { setData(d); setErr(""); } }).catch((e) => alive && setErr(e.message));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, version, n, ...deps]);
  return [data, () => setN((x) => x + 1), err];
}

/** Clickable citation chip → opens the exact clause highlighted in the original PDF. */
export function Cite({ c }: { c: Any }) {
  if (!c) return null;
  return (
    <span className={`cite ${c.verified ? "" : "unverified"}`}
      title={(c.quote || "") + (c.verified ? "" : "\n⚠ quote not verified against the contract")}
      onClick={() => nav("viewer", { contract: c.contract_id, clause: c.clause_number, v: c.version ?? undefined })}>
      {c.contract_id} §{c.clause_number}{c.verified ? "" : " ⚠"}
    </span>
  );
}

export function Cites({ cs }: { cs?: Any[] }) {
  if (!cs?.length) return null;
  return <span className="cites">{cs.map((c, i) => <Cite key={i} c={c} />)}
    <button className="link" onClick={() => nav("viewer", { contract: cs[0].contract_id, clause: cs[0].clause_number,
      v: cs[0].version ?? undefined })}>View references</button></span>;
}

export const Sev = ({ s }: { s: string | number }) => <span className={`sev sev-${s}`}>{String(s)}</span>;

export const Src = ({ k }: { k: "sourced" | "analysis" }) =>
  <span className={`src ${k}`}>{k === "sourced" ? "SOURCED" : "ANALYSIS"}</span>;

export const Status = ({ s }: { s?: string }) => <span className={`status st-${s}`}>{s}</span>;

export function Err({ e }: { e?: string }) {
  return e ? <div className="err">{e}</div> : null;
}

export function Busy({ run, label }: { run: () => Promise<unknown>; label: string }) {
  const [b, setB] = useState(false);
  const [e, setE] = useState("");
  return <>
    <button disabled={b} onClick={() => { setB(true); setE(""); run().catch((x) => setE(x.message)).finally(() => setB(false)); }}>
      {b ? "…" : label}</button>{e && <span className="err inline">{e}</span>}
  </>;
}
