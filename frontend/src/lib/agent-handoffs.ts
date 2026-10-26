import { text, type ApiRecord } from './api';
import { activityInstant } from './activity-time';

const ORDER = ['odin', 'thor', 'norns', 'loki', 'heimdall', 'tyr', 'synth', 'all'];
export const AGENT_ROLES: Record<string, string> = { odin: 'Orchestrator', thor: 'Extraction', norns: 'Timeline', loki: 'Adversarial review', heimdall: 'Verification', tyr: 'Arbitration & action', synth: 'Report synthesis', all: 'Shared team message', system: 'System' };
export const agentLabel = (id: string) => id === 'all' ? 'All agents' : id ? id[0].toUpperCase() + id.slice(1) : 'Unspecified';
export type Handoff = { id: string; sender: string; receiver: string; message: ApiRecord; at?: string };
export function agentHandoffs(messages: ApiRecord[]) {
 const steps: Handoff[] = messages.map((m, i) => ({ id: text(m.id, `message-${i}`), sender: text(m.sender, '').trim().toLowerCase(), receiver: text(m.receiver, '').trim().toLowerCase(), message: m, at: activityInstant(m.ts ?? m.ended_at) }));
 const routed = steps.filter(m => m.sender && m.receiver);
 const agents = [...new Set(routed.flatMap(m => [m.sender, m.receiver]))].sort((a, b) => {
  const rank = (v: string) => ORDER.includes(v) ? ORDER.indexOf(v) : ORDER.length;
  return rank(a) - rank(b) || a.localeCompare(b);
 });
 const connections = new Map<string, { id: string; source: string; target: string; steps: Handoff[] }>();
 for (const step of routed) {
  const id = JSON.stringify([step.sender, step.receiver]);
  const edge = connections.get(id) ?? { id, source: step.sender, target: step.receiver, steps: [] };
  edge.steps.push(step); connections.set(id, edge);
 }
 return { steps, agents, connections: [...connections.values()], unrouted: steps.length - routed.length };
}
