'use client';
import { useEffect, useId, useMemo, useState } from 'react';
import { Background, BaseEdge, Controls, EdgeLabelRenderer, Handle, MarkerType, Position, ReactFlow, ReactFlowProvider, type Edge, type EdgeProps, type Node, type NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { ArrowLeft, ArrowRight, Pause, Play, Radio, RotateCcw, Square } from 'lucide-react';
import { AGENT_ROLES, agentHandoffs, agentLabel } from '@/lib/agent-handoffs';
import { nextReplayIndex } from '@/lib/message-context';
import { MessageDetails } from './message-details';
import { activityTimeText } from '@/lib/activity-time';
import { text, type ApiRecord } from '@/lib/api';
import { useWorkspace } from './providers';
import { Badge, Button, Panel, PanelTitle } from './ui';
import { Citations, Status } from './api-ui';

type AgentNode = Node<{ label: string; agent: string; active: boolean }, 'agent'>;
function Agent({ data }: NodeProps<AgentNode>) {
 return <div className={'handoff-node' + (data.active ? ' active' : '')}>{(['top', 'right', 'bottom', 'left'] as const).map(side => <span key={side}><Handle type="source" id={'out-' + side} position={Position[side[0].toUpperCase() + side.slice(1) as keyof typeof Position]} /><Handle type="target" id={'in-' + side} position={Position[side[0].toUpperCase() + side.slice(1) as keyof typeof Position]} /></span>)}<span className="handoff-agent-symbol">{data.label[0]}</span><strong>{data.label}</strong><small>{AGENT_ROLES[data.agent] ?? 'Recorded participant'}</small></div>;
}
function HandoffEdge({ id, sourceX, sourceY, targetX, targetY, markerEnd, style, label, data }: EdgeProps) {
 const dx = targetX - sourceX, dy = targetY - sourceY; const length = Math.max(1, Math.hypot(dx, dy));
 const cx = (sourceX + targetX) / 2 - dy / length * 52; const cy = (sourceY + targetY) / 2 + dx / length * 52;
 const path = `M ${sourceX} ${sourceY} Q ${cx} ${cy} ${targetX} ${targetY}`;
 const x = (sourceX + 2 * cx + targetX) / 4, y = (sourceY + 2 * cy + targetY) / 4;
 return <><BaseEdge id={id} path={path} markerEnd={markerEnd} style={style} interactionWidth={24} />{data?.replaying ? <circle key={String(data.messageId)} className="handoff-packet" r="5" fill="var(--theme-accent, #3971e7)"><animateMotion dur={String(data.duration) + 'ms'} repeatCount="indefinite" path={path} /></circle> : null}<EdgeLabelRenderer><span className="handoff-edge-count" style={{ transform: `translate(-50%, -50%) translate(${x}px, ${y}px)` }}>{label}</span></EdgeLabelRenderer></>;
}
const edgeTypes = { handoff: HandoffEdge };
const nodeTypes = { agent: Agent };
export function AgentHandoffView({ messages, running = false, scope, context = {} }: { messages: ApiRecord[]; running?: boolean; scope: string; context?: ApiRecord }) {
 const { timeZone, demo } = useWorkspace(); const [picked, setPicked] = useState(''); const [showAll, setShowAll] = useState(false); const rangeId = useId();
 const [replayMessages, setReplayMessages] = useState<ApiRecord[] | null>(null); const [playing, setPlaying] = useState(false); const [delay, setDelay] = useState(2000);
 const source = replayMessages ?? messages;
 const model = useMemo(() => agentHandoffs(source), [source]);
 const selectedIndex = picked ? model.steps.findIndex(s => s.id === picked) : model.steps.length - 1;
 const index = selectedIndex < 0 ? model.steps.length - 1 : selectedIndex; const selected = model.steps[index];
 useEffect(() => {
  if (!playing) return;
  const timer = setTimeout(() => {
   const next = nextReplayIndex(index, model.steps.length);
   if (next === null) setPlaying(false); else setPicked(model.steps[next].id);
  }, delay);
  return () => clearTimeout(timer);
 }, [playing, index, model.steps, delay]);
 const play = () => {
  if (playing) { setPlaying(false); return; }
  if (replayMessages && index >= 0 && index < model.steps.length - 1) { setPlaying(true); return; }
  const captured = messages.map(m => ({ ...m })); const first = agentHandoffs(captured).steps[0];
  if (!first) return;
  setReplayMessages(captured); setPicked(first.id); setPlaying(true);
 };
 const restart = () => {
  const captured = messages.map(m => ({ ...m })); const first = agentHandoffs(captured).steps[0];
  if (!first) return;
  setReplayMessages(captured); setPicked(first.id); setPlaying(true);
 };
 const stop = () => { setPlaying(false); setReplayMessages(null); setPicked(''); };
 const selectStep = (id: string) => { setPlaying(false); setPicked(id); };
 const positions = new Map(model.agents.map((a, i) => { const angle = -Math.PI / 2 + i * 2 * Math.PI / Math.max(1, model.agents.length); return [a, { x: 300 + Math.cos(angle) * Math.max(340, model.agents.length * 40), y: 190 + Math.sin(angle) * Math.max(245, model.agents.length * 29) }] as const; }));
 const nodes: AgentNode[] = model.agents.map(a => ({ id: a, type: 'agent', position: positions.get(a)!, data: { agent: a, label: agentLabel(a), active: selected?.sender === a || selected?.receiver === a } }));
 const edges: Edge[] = model.connections.map(e => {
  const a = positions.get(e.source)!, b = positions.get(e.target)!; const dx = b.x - a.x, dy = b.y - a.y;
  const side = Math.abs(dx) > Math.abs(dy) ? dx > 0 ? 'right' : 'left' : dy > 0 ? 'bottom' : 'top';
  const opposite = { right: 'left', left: 'right', top: 'bottom', bottom: 'top' }[side];
  const active = selected?.sender === e.source && selected?.receiver === e.target;
  return { id: e.id, source: e.source, target: e.target, sourceHandle: 'out-' + side, targetHandle: 'in-' + opposite, type: 'handoff', label: String(e.steps.length), markerEnd: { type: MarkerType.ArrowClosed, color: active ? 'var(--theme-accent, #3971e7)' : 'var(--theme-text, #60748f)' }, style: { stroke: active ? 'var(--theme-accent, #3971e7)' : 'var(--theme-border-blue, #b7c9e2)', strokeWidth: active ? 3 : 1.5 }, labelStyle: { fill: 'var(--theme-ink, #253c5c)', fontSize: 12 }, labelBgStyle: { fill: 'var(--theme-surface, #fff)' }, animated: active && playing, data: { replaying: active && playing, messageId: selected?.id, duration: delay }, ariaLabel: `${agentLabel(e.source)} to ${agentLabel(e.target)}: ${e.steps.length} recorded messages` };
 });
 const displayedEdges = showAll ? edges : edges.filter(e => e.source === selected?.sender && e.target === selected?.receiver);
 const choose = (next: number) => { if (model.steps[next]) selectStep(model.steps[next].id); };
 return <Panel className={'handoff-panel' + (playing ? ' is-simulating' : '')}><PanelTitle title="Who contacted whom" description={scope}><Badge tone={running && !demo ? 'green' : 'neutral'}>{running && !demo ? <><Radio size={12} /> Updating live</> : demo ? 'Sample messages' : 'Recorded messages'}</Badge></PanelTitle>
 {model.steps.length ? <>{model.agents.length > 0 ? <><div className="handoff-view-controls"><label>Connections<select value={showAll ? 'all' : 'focused'} onChange={e => setShowAll(e.target.value === 'all')}><option value="focused">Selected exchange</option><option value="all">All recorded exchanges</option></select></label><span>{showAll ? 'All recorded connections. Select a link to highlight its message.' : 'One exchange at a time. Choose a connection below or step through messages.'}</span></div><div className="handoff-canvas" role="region" aria-label="Recorded agent communication map"><ReactFlowProvider><ReactFlow key={model.agents.join('|')} nodes={nodes} edges={displayedEdges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} fitView fitViewOptions={{ padding: .08 }} minZoom={.35} maxZoom={1.8} nodesDraggable={false} nodesConnectable={false} onEdgeClick={(_, edge) => { const connection = model.connections.find(e => e.id === edge.id); if (connection?.steps.length) selectStep(connection.steps[connection.steps.length - 1].id); }} onNodeClick={(_, node) => { const step = [...model.steps].reverse().find(s => s.sender === node.id || s.receiver === node.id); if (step) selectStep(step.id); }} proOptions={{ hideAttribution: true }}><Background gap={22} color="var(--theme-border-blue, #d9e5f6)" /><Controls showInteractive={false} /></ReactFlow></ReactFlowProvider></div></> : <p className="muted-note">These messages do not include complete sender/recipient pairs. Their recorded contents are available below; no connections have been inferred.</p>}
 <div className="handoff-connections" aria-label="Recorded communication links">{model.connections.map(c => <button key={c.id} className={selected?.sender === c.source && selected?.receiver === c.target ? 'active' : ''} onClick={() => selectStep(c.steps[c.steps.length - 1].id)}>{agentLabel(c.source)} → {agentLabel(c.target)} <b>{c.steps.length}</b></button>)}</div>
 <div className="handoff-simulation"><div className="button-row"><Button onClick={play} disabled={!model.steps.length}>{playing ? <><Pause size={14} />Pause simulation</> : <><Play size={14} />{replayMessages && index < model.steps.length - 1 ? 'Resume simulation' : 'Play simulation'}</>}</Button>{replayMessages && <><Button variant="secondary" onClick={restart}><RotateCcw size={14} />Restart</Button><Button variant="ghost" onClick={stop}><Square size={13} />Stop simulation</Button></>}<label>Replay speed<select value={delay} onChange={e => setDelay(Number(e.target.value))}><option value={4000}>Slow · 4s per message</option><option value={2000}>Normal · 2s per message</option><option value={1000}>Fast · 1s per message</option></select></label></div><p role="status">{replayMessages ? playing ? 'Simulation playing: replaying captured messages.' : index >= model.steps.length - 1 ? 'Simulation complete.' : 'Simulation paused.' : 'Simulation is ready. Press Play to replay the recorded workflow.'} No agents are run and no model calls are made. Replay timing is illustrative; timestamps remain the recorded times.</p>{replayMessages && messages.length > replayMessages.length && <p>{messages.length - replayMessages.length} newer messages are outside this captured replay. Stop or restart to include them.</p>}</div>
 <div className="handoff-playback"><div><Button variant="secondary" aria-label="Previous recorded message" disabled={index <= 0} onClick={() => choose(index - 1)}><ArrowLeft size={14} /></Button><strong>Message {index + 1} of {model.steps.length}</strong><Button variant="secondary" aria-label="Next recorded message" disabled={index >= model.steps.length - 1} onClick={() => choose(index + 1)}><ArrowRight size={14} /></Button><button className="text-link" onClick={stop}>Follow latest</button></div><label htmlFor={rangeId} className="sr-only">Replay recorded agent messages</label><input id={rangeId} type="range" min="0" max={Math.max(0, model.steps.length - 1)} value={Math.max(0, index)} onChange={e => choose(Number(e.target.value))} /></div>
 {selected && <article className="handoff-selected" aria-live="polite"><header><strong>{agentLabel(selected.sender)} → {agentLabel(selected.receiver)}</strong><Status value={selected.message.kind} /><time dateTime={selected.at} title={'Original timestamp: ' + text(selected.message.ts ?? selected.message.ended_at)}>{activityTimeText(selected.message.ts ?? selected.message.ended_at, timeZone)}</time></header><p>{text(selected.message.summary)}</p>{selected.message.contract_id ? <small>Agreement: {text(selected.message.contract_id)}</small> : null}<Citations values={selected.message.citations} /><MessageDetails message={selected.message} context={context} /></article>}
 <p className="handoff-note">Arrows show the selected connection unless all exchanges are enabled; counts include all messages in this scope. Agents may work in parallel, so this is a communication map rather than an execution dependency graph.{model.unrouted ? ` ${model.unrouted} messages have no complete sender/recipient pair and cannot be drawn as arrows.` : ''}</p></> : <p className="muted-note">No agent messages recorded yet. Connections appear as the agents publish their handoffs.</p>}
 <p className="handoff-time-note">Activity times are displayed in {timeZone}. Contract effective dates and the simulated clock are separate from upload and run times.</p>
 </Panel>;
}
