import { useMemo, useState } from "react";
import { Background, Controls, Edge, MarkerType, Node, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Any, nav } from "../api";
import { Err, useApi } from "../components";

const EDGE_COLOR: Record<string, string> = {
  conflicts_with: "#dc2626", depends_on: "#2563eb", supersedes: "#7c3aed", governs: "#059669",
  party_to: "#9ca3af", contains: "#d1d5db",
};

/** FR9.1 — contracts, clauses and parties as nodes; dependencies and conflicts as edges. */
export default function GraphView() {
  const [g, , err] = useApi("/graph");
  const [sel, setSel] = useState<Any>(null);

  const { nodes, edges } = useMemo(() => {
    if (!g) return { nodes: [] as Node[], edges: [] as Edge[] };
    const contracts = g.nodes.filter((n: Any) => n.type === "contract");
    const parties = g.nodes.filter((n: Any) => n.type === "party");
    const clauses = g.nodes.filter((n: Any) => n.type === "clause");
    const pos: Record<string, { x: number; y: number }> = {};
    const R = 260, cx = 450, cy = 330;
    contracts.forEach((n: Any, i: number) => {
      const a = (2 * Math.PI * i) / Math.max(contracts.length, 1);
      pos[n.id] = { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) };
    });
    parties.forEach((n: Any, i: number) => { pos[n.id] = { x: 40 + i * 190, y: 0 }; });
    const perContract: Record<string, number> = {};
    clauses.forEach((n: Any) => {
      const k = `c:${n.contract_id}`;
      const i = (perContract[k] = (perContract[k] ?? 0) + 1);
      const p = pos[k] ?? { x: cx, y: cy };
      const dx = p.x - cx, dy = p.y - cy, len = Math.hypot(dx, dy) || 1;
      pos[n.id] = { x: p.x + (dx / len) * 150 + (i - 1) * 25, y: p.y + (dy / len) * 110 + (i - 1) * 42 };
    });
    const nodes: Node[] = g.nodes.map((n: Any) => ({
      id: n.id, position: pos[n.id] ?? { x: 0, y: 0 }, data: { label: n.label, raw: n },
      className: `gnode ${n.type}`,
    }));
    const edges: Edge[] = g.edges.map((e: Any, i: number) => ({
      id: `e${i}`, source: e.source, target: e.target, label: e.kind === "conflicts_with" || e.kind === "depends_on" ? e.kind : undefined,
      animated: e.kind === "conflicts_with", data: e,
      style: { stroke: EDGE_COLOR[e.kind] ?? "#999", strokeWidth: e.kind === "conflicts_with" ? 2.5 : 1.2 },
      markerEnd: e.kind === "depends_on" ? { type: MarkerType.ArrowClosed, color: EDGE_COLOR.depends_on } : undefined,
    }));
    return { nodes, edges };
  }, [g]);

  return (
    <div className="graphpage">
      <Err e={err} />
      <div className="legend">{Object.entries(EDGE_COLOR).map(([k, c]) => <span key={k}><i style={{ background: c }} />{k}</span>)}</div>
      <div className="flow">
        <ReactFlow nodes={nodes} edges={edges} fitView
          onNodeClick={(_, n) => setSel({ node: n.data.raw })} onEdgeClick={(_, e) => setSel({ edge: e.data })}>
          <Background /><Controls />
        </ReactFlow>
      </div>
      {sel && <div className="card">
        {sel.node && <>
          <b>{sel.node.label}</b> <span className="tag">{sel.node.type}</span>
          {sel.node.type === "contract" && <button onClick={() => nav("contract", { id: sel.node.contract_id })}>Open</button>}
          {sel.node.type === "clause" && <button onClick={() => nav("viewer", { contract: sel.node.contract_id, clause: sel.node.clause_number })}>View clause</button>}
        </>}
        {sel.edge && <><b>{sel.edge.kind}</b>: {sel.edge.reason}
          {sel.edge.finding_id && <button onClick={() => nav("debate")}>See debate</button>}</>}
      </div>}
    </div>
  );
}
