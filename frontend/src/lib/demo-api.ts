// Browser-only preview fixtures. Never used as a fallback for failed live requests.
import { demoPortfolio as p } from './demo-data';
import { projectPortfolio, monthEnds, projectObligation } from './simulation';
import { record, text, type ApiRecord, type Citation } from './api';
const citation = (o: typeof p.obligations[number]): Citation => ({ contract_id: o.contractId, clause_number: o.clause, quote: o.quote, page: 1, version: 1, verified: false });
const contracts = p.contracts.map(c => ({ id: c.id, title: c.name, type: c.category, parties: [{ name: c.party, role: 'counterparty' }], version: 1, health_score: null, analysed: true, parse_warnings: ['Preview fixture. No original document has been uploaded.'], source: 'analysis', clauses: p.obligations.filter(o => o.contractId === c.id).map(o => ({ number: o.clause, heading: o.title, clause_type: o.type, page: 1, text: o.quote, citation: citation(o), source: 'sourced' })), extraction: { fields: p.obligations.filter(o => o.contractId === c.id).map(o => ({ name: o.title, value: o.deadline, confidence: o.confidence, status: 'unverified', citation: citation(o), source: 'analysis' })), flags: [] }, versions: [{ version: 1, created_at: p.asOf }], health: null }));
let actions: ApiRecord[] = p.actions.map(a => { const o = p.obligations.find(o => o.id === a.obligationId)!; return { id: a.id, contract_id: o.contractId, kind: a.id === 'a1' ? 'non_renewal_notice' : a.id === 'a2' ? 'payment_instruction' : 'escalation_memo', subject: a.title, body_md: a.draft, to: a.id === 'a1' ? 'legal@cobalt.example.test' : 'finance@northstar.example.test', status: 'draft', deadline: o.deadline, confidence: o.confidence, needs_approval: true, citations: [citation(o)], source: 'analysis' }; });
export async function demoRequest(path: string, options: RequestInit = {}): Promise<unknown> {
  if (options.signal?.aborted) throw new DOMException('Aborted', 'AbortError');
  const url = new URL(path, 'https://preview.invalid');
  const route = url.pathname;
  const method = options.method ?? 'GET';
  const date = url.searchParams.get('as_of') ?? p.asOf;
  const projection = projectPortfolio(p, date);
  const alerts = projection.urgent.map(o => ({ id: 'alert-' + o.id, contract_id: o.contractId, kind: o.type.toLowerCase(), severity: o.remaining < 0 ? 'high' : 'medium', title: o.title, why: 'Sample obligation requires review at the selected date.', due_date: o.deadline, status: 'open', citations: [citation(o)], source: 'analysis' }));
  if (method !== 'GET') {
    const body = typeof options.body === 'string' ? record(JSON.parse(options.body)) : {};
    if (route === '/api/clock') return { sim_now: body.sim_now };
    if (/^\/api\/actions\/[^/]+$/.test(route) && method === 'PATCH') { const a = actions.find(a => a.id === route.split('/')[3]); if (!a) throw new Error('Draft not found'); Object.assign(a, body); return a; }
    if (/^\/api\/actions\/[^/]+\/(approve|reject)$/.test(route)) { const a = actions.find(a => a.id === route.split('/')[3]); if (a) a.status = route.endsWith('/approve') ? 'approved' : 'rejected'; return a; }
    throw new Error('This operation needs the connected backend. Preview mode does not upload, send email, or run agents.');
  }
  if (route === '/api/clock') return { sim_now:p.asOf, real_today:p.asOf };
  if (route === '/api/contracts') return contracts;
  const contractId = route.match(/^\/api\/contracts\/([^/]+)$/)?.[1];
  if (contractId) return contracts.find(c => c.id === contractId);
  if (route === '/api/dashboard') return { exposure: { expected: projection.triggered, worst_case: projection.potential, currency: 'USD', contracts: p.contracts.map(c => ({ contract_id: c.id, title: c.name, amount: projection.obligations.filter(o => o.contractId === c.id).reduce((sum,o) => sum + o.potential,0), assumptions: ['Illustrative preview: no corrective action is taken.'], source: 'analysis' })) }, heatmap: { cells: monthEnds(date).flatMap(month => p.obligations.map(o => ({ contract_id: o.contractId, clause_type: o.type, month: month.date.slice(0,7), amount: projectObligation(o, month.date).triggered }))) }, alerts, health: {} };
  if (route === '/api/timeline') return { entries: projection.obligations.filter(o => !url.searchParams.get('contract_id') || o.contractId === url.searchParams.get('contract_id')).map(o => ({ id: o.id, contract_id: o.contractId, date: o.deadline, kind: o.type.toLowerCase(), title: o.title, status: o.remaining < 0 ? 'missed' : o.remaining === 0 ? 'due' : 'upcoming', amount: { amount: o.potential, currency: 'USD' }, citation: citation(o), owner: 'Legal operations', source: 'analysis' })) };
  if (route === '/api/alerts') return alerts;
  if (route === '/api/actions') return actions;
  if (/^\/api\/actions\/[^/]+$/.test(route)) return actions.find(a => a.id === route.split('/')[3]);
  if (route === '/api/events') return p.events.map(e => ({ id: e.id, subject: e.title, description: e.body, date: e.date, contracts: [e.contractId], status: 'processed', parse_method: 'demo', source: 'analysis' }));
  if (route === '/api/debate') return { findings: p.obligations.filter(o => p.findings.some(f => f.obligationId === o.id)).map(o => ({ id: o.id, contract_id: o.contractId, title: o.title, status: 'open', severity: 3, likelihood: .6, source: 'analysis', citations: [citation(o)], debate: p.findings.filter(f => f.obligationId === o.id).map(f => ({ sender: f.agent, kind: f.kind.toLowerCase(), summary: f.body, ts: f.timestamp, source: 'analysis' })) })), rulings: [], messages: p.findings.map(f => ({ id: f.id, sender: f.agent, kind: f.kind.toLowerCase(), summary: f.body, ts: f.timestamp })) };
  if (route === '/api/graph') return {
    nodes: contracts.flatMap((c,i) => [{ id:'c:'+c.id,type:'contract',label:c.title,contract_id:c.id },{id:'party-'+c.id,type:'party',label:p.contracts[i].party},...c.clauses.map(o=>({id:c.id+'-'+o.number,type:'clause',label:'§'+o.number+' · '+o.heading,contract_id:c.id,clause_number:o.number,version:1}))]),
    edges: contracts.flatMap(c=>[{source:'party-'+c.id,target:'c:'+c.id,kind:'party_to'},...c.clauses.map(o=>({source:'c:'+c.id,target:c.id+'-'+o.number,kind:'contains'}))]),
    cascades: {}
  };
  if (route === '/api/runs') return [{ id: 'preview-run', kind: 'analysis', status: 'partial', started_at: p.asOf + 'T09:00:00Z', workplan: { workstreams: contracts.map(c => ({ id: 'ws:' + c.id, contract_id: c.id, status: 'partial', evidence_score: .6, reason: 'Sample text only; original documents are not available in preview.', tasks: [] })) }, budget: { agent_calls: 4, tool_calls: 0, tokens_in: 0, tokens_out: 0, usd: 0, fallbacks: 0 } }];
  if (route === '/api/report-index') return { runs: [], contracts: [], events: p.events.map(e => ({ event_id: e.id, subject: e.title, date: e.date, contract_ids: [e.contractId], run_ids: [], status: 'processed' })) };
  if (route === '/api/workflow/preview-run') {
    const run = (await demoRequest('/api/runs') as ApiRecord[])[0];
    return { run, workstreams: record(run.workplan).workstreams, timeline: { running: false, tool_call_count: 0, agents: {}, steps: p.findings.map(f => ({ id: f.id, sender: f.agent, receiver: 'odin', kind: f.kind.toLowerCase(), summary: f.body, ended_at: f.timestamp, tool_calls: [] })) }, outputs: { finding: [], violation: [], alert: [], action: [] }, debate: [], reports: [], remarks: { decision: 'partial', complete: false, gaps: [{ contract_id: 'Preview', status: 'partial', reason: 'Sample text only; no agents ran and no verified report was generated.' }] } };
  }
  if (route === '/api/runs/preview-run') return { id: 'preview-run', status: 'partial', messages: p.findings.map(f => ({ sender: f.agent, summary: f.body, ts: f.timestamp, kind: f.kind.toLowerCase() })), tool_calls: [], budget: { per_agent: {} } };
  if (route === '/api/violations') return [];
  if (route === '/api/email/template') return 'Subject: Payment update\nContract: [contract id]\nDate: [YYYY-MM-DD]\nAmount: [amount and currency]\nDetails: [event details]';
  if (route === '/api/email/status') return { status: 'preview', error: 'Gmail is not connected in preview.' };
  if (route.startsWith('/api/reports/')) return { executive_summary: 'Preview workspace with four illustrative agreements. Connect the backend to generate a verified report.', completeness: { status: 'partial', gaps: ['Original documents are not available.'] }, references: [] };
  if (route === '/api/observability') return { runs: await demoRequest('/api/runs'), citation_guard: { checked: 0, verified: 0, blocked: 0, stored_citations: 0, stored_unverified: 4 }, limits: {}, providers: {} };
  if (route === '/api/insights/calibration') return { buckets: [] };
  if (route === '/api/insights/counterparties') return [];
  if (route === '/api/tools') return [];
  if (route.includes('/diff')) return { changes: [] };
  if (route.includes('/lineage/')) return { versions: [] };
  if (route.startsWith('/api/citation/')) throw new Error('No original PDF exists for preview fixtures. Upload a contract through the connected backend to view verified references.');
  throw new Error('This view needs the connected backend.');
}

const initialActions = JSON.stringify(actions);
export function resetDemo() { actions = JSON.parse(initialActions); }
