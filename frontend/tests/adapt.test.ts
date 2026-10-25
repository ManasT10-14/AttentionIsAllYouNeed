import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
process.env.NEXT_PUBLIC_API_BASE_URL = '/';
const client = import('../src/lib/api');
// Real backend responses captured in docs/api-samples.
const sample = (name: string) => JSON.parse(readFileSync(new URL('../../docs/api-samples/' + name + '.json', import.meta.url), 'utf8'));

test('backend payloads gain the field names the UI reads', async () => {
  const { adaptPayload, validatePayload } = await client;
  const contracts = sample('contracts');
  adaptPayload('/api/contracts', contracts);
  assert.equal(new Set(contracts.map((c: { id: string }) => c.id)).size, contracts.length, 'contract rows need unique ids');
  assert.ok(contracts.every((c: { id: string; contract_id: string }) => c.id === c.contract_id));

  const detail = sample('contracts_MSA-2026-001');
  adaptPayload('/api/contracts/MSA-2026-001', detail);
  assert.ok(detail.extraction.fields.length > 5, 'extraction becomes a field list');
  assert.ok(detail.extraction.fields.every((f: { name: string }) => typeof f.name === 'string'));

  const timeline = sample('timeline_contract_id_MSA-2026-001');
  adaptPayload('/api/timeline', timeline);
  validatePayload('/api/timeline', timeline);
  assert.ok(timeline.entries.length > 0, 'per-contract entries are flattened');

  const actions = sample('actions');
  adaptPayload('/api/actions', actions);
  assert.ok(actions.every((a: { needs_approval: unknown; needs_human_approval: unknown }) => a.needs_approval === a.needs_human_approval));

  const events = sample('events');
  adaptPayload('/api/events', events);
  assert.equal(events[0].date, events[0].occurred_at);
});
