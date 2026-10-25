import test from 'node:test';
import assert from 'node:assert/strict';
import { reportRuns, runReportTarget, runTitle } from '../src/lib/run-presentation';

test('run titles explain analysis scope, updates, and event subjects', () => {
 assert.equal(runTitle({ kind: 'analysis', workplan: { workstreams: [{ contract_id: 'C01' }, { contract_id: 'C02' }, { contract_id: 'cross' }] } }), 'Contract analysis · 2 agreements');
 assert.equal(runTitle({ kind: 'update', workplan: { links: { contract_id: 'C01' } } }, [{ id: 'C01', title: 'Supply agreement' }]), 'Contract update · Supply agreement');
 assert.equal(runTitle({ kind: 'event', workplan: { links: { event_id: 'ev1' } } }, [], [{ id: 'ev1', subject: 'Invoice overdue' }]), 'Event review · Invoice overdue');
 assert.equal(runTitle({ kind: 'ask' }), 'Contract question');
 assert.equal(runTitle({ kind: 'analysis', title: 'Targeted contract review' }), 'Targeted contract review');
});

test('report lists retain runs without snapshots and merge saved metadata newest first', () => {
 const rows = reportRuns([{ run_id: 'old', run_kind: 'analysis', generated_at: '2026-10-24T09:00:00Z' }], [
  { id: 'new', kind: 'event', started_at: '2026-10-25T09:00:00Z' },
  { id: 'old', kind: 'analysis', started_at: '2026-10-24T08:00:00Z', workplan: { workstreams: [{ contract_id: 'C01' }] } },
 ]);
 assert.deepEqual(rows.map(r => r.run_id), ['new', 'old']);
 assert.equal(rows[0].has_snapshot, false);
 assert.equal(rows[1].has_snapshot, true);
 assert.match(runTitle(rows[1]), /C01/);
});

test('report selection uses event reports when a workflow snapshot does not exist', () => {
 assert.deepEqual(runReportTarget({ run: { id: 'r1' }, event_id: 'e1', reports: [{ kind: 'event' }] }), { kind: 'event', id: 'e1' });
 assert.deepEqual(runReportTarget({ run: { id: 'r1' }, event_id: 'e1', reports: [{ kind: 'run' }, { kind: 'event' }] }), { kind: 'run', id: 'r1' });
 assert.equal(runReportTarget({ run: { id: 'r1', status: 'failed' }, reports: [] }), null);
 assert.equal(runReportTarget({ reports: [{ kind: 'event' }] }), null);
});

test('preview report navigation exposes execution without implying agents actually ran', async () => {
 const { demoRequest } = await import('../src/lib/demo-api');
 const index = await demoRequest('/api/report-index') as { runs: unknown[] };
 const workflow = await demoRequest('/api/workflow/preview-run') as Record<string, unknown>;
 assert.deepEqual(index.runs, []);
 assert.equal(runReportTarget(workflow), null);
 assert.equal((workflow.run as Record<string, unknown>).status, 'partial');
 assert.ok((workflow.timeline as { steps: unknown[] }).steps.length > 0);
});
