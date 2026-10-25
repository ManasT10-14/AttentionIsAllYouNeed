export type ApiRecord = Record<string, unknown>;
export type Source = 'sourced' | 'analysis';
export type Citation = { contract_id: string; clause_number: string; quote?: string; page?: number; version?: number; verified?: boolean };
export type Money = { amount: number; currency: string };
export type ApiUser = { id?: string; email: string; name?: string; role: string };
export type Session = { user: ApiUser; company?: ApiRecord & { sim_now?: string }; gmail_connected?: boolean; gmail_address?: string; google_configured?: boolean; dev_login?: boolean };
export type Dashboard = ApiRecord & { exposure?: { expected: number; worst_case: number; currency: string; contracts: ApiRecord[] }; heatmap?: { cells: { contract_id: string; clause_type: string; month: string; amount: number }[] }; alerts?: ApiRecord[]; health?: Record<string, number | null> };
export type GraphNode = ApiRecord & { id: string; type: 'contract' | 'party' | 'clause'; label: string };
export type GraphEdge = ApiRecord & { source: string; target: string; kind: string; reason?: string; severity?: number | string; finding_id?: string };
export type Graph = { nodes: GraphNode[]; edges: GraphEdge[]; cascades?: Record<string, string[]> };
export type CitationResolution = ApiRecord & { page: number; bboxes: number[][]; text: string; pdf_url: string };

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? '').trim() === '/' ? '/' : (process.env.NEXT_PUBLIC_API_BASE_URL ?? '').trim().replace(/\/$/, '');
export const apiConfigured = Boolean(API_BASE);
export function apiUrl(path: string) {
  if (!apiConfigured) throw new Error('Backend is not connected. Set NEXT_PUBLIC_API_BASE_URL or explore the demo.');
  if (!path.startsWith('/api/') && path !== '/openapi.json') throw new Error('Invalid API path.');
  return (API_BASE === '' || API_BASE === '/' ? '' : API_BASE) + path;
}
export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) { super(message); this.name = 'ApiError'; }
}
export function record(value: unknown): ApiRecord { return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as ApiRecord : {}; }
export function list(value: unknown, key?: string): ApiRecord[] {
  const target = key ? record(value)[key] : value;
  return Array.isArray(target) ? target.map(record) : [];
}
export function collection(value: unknown, ...keys: string[]): ApiRecord[] {
  if (Array.isArray(value)) return list(value);
  for (const key of keys) if (Array.isArray(record(value)[key])) return list(value, key);
  throw new Error('Unexpected list response from backend. Check the backend response samples.');
}
export const text = (value: unknown, fallback = 'Not provided'): string => typeof value === 'string' || typeof value === 'number' ? String(value) : fallback;
export const number = (value: unknown): number | undefined => typeof value === 'number' && Number.isFinite(value) ? value : undefined;
export const id = (value: unknown): string => text(record(value).id, '');
export function query(path: string, values: Record<string, string | number | boolean | undefined>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value !== undefined && value !== '') params.set(key, String(value)); });
  return path + (params.size ? '?' + params : '');
}
export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const signal = options.signal ? AbortSignal.any([options.signal, AbortSignal.timeout(30000)]) : AbortSignal.timeout(30000);
  const response = await fetch(apiUrl(path), { ...options, headers, signal, credentials: 'include', cache: 'no-store' });
  const plainText = path.split('?')[0] === '/api/email/template' && response.ok;
  const body: unknown = response.status === 204 ? null : plainText ? await response.text() : await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && typeof window !== 'undefined') window.dispatchEvent(new Event('odin-session-expired'));
    throw new ApiError(response.status, text(record(record(body).detail).error ?? record(body).detail ?? record(body).error, 'Request failed (' + response.status + ').'), body);
  }
  if ((options.method ?? 'GET') === 'GET') validatePayload(path, body);
  return body as T;
}
export function post<T = unknown>(path: string, body?: unknown) { return api<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }); }
export function viewerLink(citation: Citation) {
  return query('/viewer', { contract: citation.contract_id, clause: citation.clause_number, v: citation.version });
}
export function formatMoney(value: unknown, currency?: string) {
  const amount = number(record(value).amount) ?? number(value);
  const code = text(record(value).currency, currency ?? '');
  if (amount === undefined || !code) return 'Not provided';
  try { return new Intl.NumberFormat(code === 'INR' ? 'en-IN' : 'en-US', { style: 'currency', currency: code, maximumFractionDigits: 0 }).format(amount); }
  catch { return code + ' ' + amount.toLocaleString(); }
}
export function dateText(value: unknown) {
  const s = text(value, '');
  const date = new Date(s.length === 10 ? s + 'T00:00:00Z' : s);
  return !s || Number.isNaN(date.getTime()) ? 'Not provided' : date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}
export function today() { return new Date().toISOString().slice(0, 10); }
export function offsetDate(date: string, days: number) { const d = new Date(date + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0, 10); }
export function daysBetween(a: string, b: string) { return Math.round((Date.parse(b + 'T00:00:00Z') - Date.parse(a + 'T00:00:00Z')) / 86400000); }

/** Checks the documented, known fields; Request types come from OpenAPI; response interfaces must be checked against backend api-samples. */
export function validatePayload(path: string, body: unknown) {
  const route = path.split('?')[0];
  const fail = () => { throw new Error('Unexpected response for ' + route + '. Check the backend response samples.'); };
  const object = record(body);
  const listKeys: Record<string,string> = { '/api/contracts':'contracts','/api/actions':'actions','/api/alerts':'alerts','/api/events':'events','/api/violations':'violations','/api/runs':'runs','/api/tools':'tools','/api/insights/health':'health','/api/insights/counterparties':'counterparties' };
  if (listKeys[route]) {
    const rows = body;
    if (!Array.isArray(rows) || rows.some(row => !row || typeof row !== 'object' || Array.isArray(row))) fail();
  }
  if (route === '/api/graph') {
    if (!Array.isArray(object.nodes) || !Array.isArray(object.edges)) fail();
    if (object.cascades !== undefined && (object.cascades === null || typeof object.cascades !== 'object' || Array.isArray(object.cascades) || Object.values(record(object.cascades)).some(ids => !Array.isArray(ids) || ids.some(id => typeof id !== 'string')))) fail();
    const nodes = list(object.nodes); const edges = list(object.edges);
    if (nodes.some(n => typeof n.id !== 'string' || typeof n.label !== 'string' || !['contract','party','clause'].includes(text(n.type,'')))) fail();
    const ids = new Set(nodes.map(n => n.id));
    if (ids.size !== nodes.length || edges.some(e => !ids.has(e.source) || !ids.has(e.target) || typeof e.kind !== 'string')) fail();
  }
  if (route === '/api/email/template' && typeof body !== 'string') fail();
  if (route === '/api/clock' && (!isIsoDate(object.sim_now) || !isIsoDate(object.real_today))) fail();
  if (route === '/api/timeline' && !Array.isArray(object.entries)) fail();
  if (route === '/api/debate' && (!Array.isArray(object.findings) || !Array.isArray(object.messages))) fail();
  if (route === '/api/dashboard') {
    if (!body || typeof body !== 'object' || Array.isArray(body)) fail();
    if (object.exposure !== undefined) {
      const e = record(object.exposure);
      if (typeof e.currency !== 'string' || !Array.isArray(e.contracts) || (number(e.expected) === undefined && number(record(e.expected).amount) === undefined) || (number(e.worst_case) === undefined && number(record(e.worst_case).amount) === undefined)) fail();
    }
    if (object.heatmap !== undefined && (!Array.isArray(record(object.heatmap).cells) || list(record(object.heatmap).cells).some(c => typeof c.contract_id !== 'string' || typeof c.clause_type !== 'string' || typeof c.month !== 'string' || number(c.amount) === undefined))) fail();
    if (object.alerts !== undefined && !Array.isArray(object.alerts)) fail();
  }
  if (route === '/api/citation/resolve' && (typeof object.text !== 'string' || !Number.isInteger(object.page) || !Array.isArray(object.bboxes) || object.bboxes.some(b => !Array.isArray(b) || b.length !== 5 || b.some(v => typeof v !== 'number')))) fail();
}

export function isIsoDate(value: unknown): value is string {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0,10) === value;
}
export function parseSession(body: unknown): Session {
  const value = record(body); const user = record(value.user);
  if (typeof user.email !== 'string' || typeof user.role !== 'string') throw new Error('The auth response must include user.email and user.role.');
  return { ...value, user } as Session;
}
export function loggedOutFlags(body: unknown): ApiRecord { return record(record(body).detail); }
export function shouldRefresh(kind: unknown) { return typeof kind === 'string' && kind !== '' && kind !== 'ping'; }
export const actionKinds = ['renewal_notice','non_renewal_notice','termination_notice','breach_notice','payment_instruction','amendment','escalation_memo'] as const;
export function deliveryOperation(kind: unknown): 'send' | 'apply' | null {
  return kind === 'amendment' ? 'apply' : actionKinds.some(k => k === kind) ? 'send' : null;
}
export function validRecipient(value: string) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim()); }
export function cascadeNodeIds(graph: Graph, contract: string) {
  return new Set(contract ? [contract,...(graph.cascades?.[contract] ?? [])].map(id => 'c:' + id) : []);
}
export function clauseTypeKey(contract: unknown, clause: unknown) { return text(contract,'') + '\u0000' + text(clause,''); }
export function indexClauseTypes(contracts: { id: string; clauses: ApiRecord[] }[]) {
  return Object.fromEntries(contracts.flatMap(c => c.clauses.map(clause => [clauseTypeKey(c.id,clause.number),text(clause.clause_type,'').toLowerCase()])));
}
