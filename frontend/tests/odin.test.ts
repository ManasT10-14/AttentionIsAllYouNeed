import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { bundleSummary, bundleWarnings, checkpointsOf, citationLabel, compareSnapshots, eventFeed, familyBadges, overrideOf, relationsOf, trackPosition } from '../src/lib/odin';
const sample = (name: string) => JSON.parse(readFileSync(new URL('../../docs/api-samples/' + name + '.json', import.meta.url), 'utf8'));

test('citation chips read "DocID ref"', () => {
  assert.equal(citationLabel({ contract_id: 'A2', clause_number: '3.2', ref: '§3.2' }), 'A2 §3.2');
  assert.equal(citationLabel({ contract_id: 'B1', clause_number: 'G' }), 'B1 Section G');
  assert.equal(citationLabel({ contract_id: 'B1', clause_number: 'G', ref: 'Section G' }), 'B1 Section G');
});
test('document families come from relations', () => {
  const rel = relationsOf(sample('bundle_import'));
  assert.deepEqual(familyBadges('STD', rel), ['Incorporated by A1, B1, C1']);
  assert.ok(familyBadges('A2', rel).includes('Incorporated by A1') && familyBadges('A2', rel).includes('Amended by A3'));
  assert.deepEqual(familyBadges('B2', rel), ['Addendum to B1']);
});
test('amended clause exposes banner data', () => {
  const o = overrideOf({ override: { by_doc: 'A3', by_ref: 'Section 1', effective: '2027-01-01', new_text: 'new' }, text: 'old' });
  assert.deepEqual(o, { by_doc: 'A3', by_ref: 'Section 1', effective: '2027-01-01', original: 'old', effectiveText: 'new' });
  assert.equal(overrideOf({ text: 'x' }), null);
});
test('bundle summary and warnings', () => {
  const s = bundleSummary(sample('bundle_import'));
  assert.equal(s.find(x => x.label === 'Ledger rows')?.value, 25);
  assert.equal(s.find(x => x.label === 'Warnings')?.value, 0);
  assert.equal(bundleWarnings(sample('bundle_import')).length, 0);
  assert.deepEqual(bundleWarnings({ warnings: ['A source warning'] }), ['A source warning']);
});
test('event feed sorts by timestamp, rejected lines last, keeps line numbers', () => {
  const feed = eventFeed([
    { id: 'bad', status: 'rejected', line: 7, source: 'drop2' },
    { id: 'two', external_id: 'E-02', occurred_at: '2027-02-10T14:15:00Z', sender: 'Nora Chen' },
    { id: 'one', external_id: 'E-01', occurred_at: '2027-01-22T09:30:00Z', sender: 'Jordan Hale' },
  ]);
  assert.deepEqual(feed.map(e => e.external_id || e.status), ['E-01', 'E-02', 'rejected']);
  assert.equal(feed[0].sender, 'Jordan Hale');
  assert.equal(feed[2].line, 7);
});
test('clock track and checkpoints', () => {
  const sim = sample('simulation');
  const cps = checkpointsOf(sim, sim.sim_now);
  assert.deepEqual(cps.map(c => c.reached), [false, false, false]);
  assert.deepEqual(checkpointsOf(sim, '2027-03-15').map(c => c.reached), [true, false, false]);
  assert.equal(trackPosition('2027-09-15', '2027-01-15', '2027-09-15'), 100);
  assert.equal(trackPosition('2026-01-01', '2027-01-15', '2027-09-15'), 0);
  assert.deepEqual(compareSnapshots({ obligations: [1], exposure: { expected: 5 } }, { obligations: [1, 2], exposure: { expected: 9 } }).filter(c => c.delta).map(c => [c.key, c.delta]), [['obligations', 1], ['exposure', 4]]);
});
