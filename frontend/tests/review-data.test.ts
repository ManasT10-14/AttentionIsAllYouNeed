import test from 'node:test';
import assert from 'node:assert/strict';
import { filterReviewMessages, hasScore, metricHistory, missingReportExplanation, qualityCoverage, reviewFindings } from '../src/lib/review-data';

test('run-scoped review never substitutes current findings for missing historical outputs', () => {
 const current = { findings: [{ id: 'new', contract_id: 'C01', claim: 'Current claim' }], rulings: [] };
 assert.deepEqual(reviewFindings(current, {}, 'old-run'), []);
 const workflow = { debate: [{ finding: { id: 'old', contract_id: 'C02' }, verifications: [{ verdict: 'challenge' }], ruling: { rationale: 'Needs proof' } }] };
 assert.equal(reviewFindings(current, workflow, 'old-run')[0].id, 'old');
 assert.equal(reviewFindings(current, workflow, 'old-run', 'C01').length, 0);
 assert.equal(reviewFindings(current, workflow, '')[0].id, 'new');
});

test('current review joins decisions to their finding rather than showing unrelated rulings', () => {
 const findings = reviewFindings({ findings: [{ id: 'one' }], rulings: [{ finding_id: 'two', winner: 'loki' }, { finding_id: 'one', winner: 'heimdall' }] }, {}, '');
 assert.deepEqual(findings[0].ruling, { finding_id: 'one', winner: 'heimdall' });
});

test('message filters preserve routing and sort history without mutating source messages', () => {
 const messages = [{ id: 'b', sender: 'loki', receiver: 'heimdall', kind: 'attack', summary: 'Invoice risk', ts: '2026-10-26T10:00:00Z' }, { id: 'a', sender: 'thor', kind: 'extract', summary: 'Extracted invoice', ts: '2026-10-26T09:00:00Z' }];
 assert.deepEqual(filterReviewMessages(messages, { agent: '', kind: '', search: '', newest: false }).map(m => m.id), ['a', 'b']);
 assert.equal(filterReviewMessages(messages, { agent: 'LOKI', kind: 'attack', search: 'invoice', newest: true })[0].receiver, 'heimdall');
 assert.deepEqual(messages.map(m => m.id), ['b', 'a']);
});

test('passing safety checks do not imply assessed contract quality', () => {
 const run = { metrics: [{ name: 'authorized_tools', status: 'passed', score: 1 }, { name: 'groundedness', status: 'skipped', score: null, reason: 'No finished workstreams' }] };
 assert.deepEqual(qualityCoverage(run), { scored: 0, total: 1, label: 'Quality not assessed' });
 assert.equal(hasScore({ status: 'passed', score: Number.NaN }), false);
 assert.equal(qualityCoverage({ metrics: [{ name: 'citation_faithfulness', score: 0, status: 'failed' }] }).scored, 1);
});

test('metric coverage separates skipped, failed, and errored attempts with their reasons', () => {
 const history = metricHistory([{ run_id: 'r1', metrics: [{ name: 'groundedness', score: null, status: 'skipped', reason: 'No workstreams' }] }, { run_id: 'r2', metrics: [{ name: 'groundedness', score: .5, status: 'failed' }] }, { run_id: 'r3', metrics: [{ name: 'groundedness', score: null, status: 'error', reason: 'Scorer failed' }] }], 'groundedness');
 assert.equal(history.scored.length, 1); assert.equal(history.skipped.length, 1); assert.equal(history.errors.length, 1);
 assert.equal(history.skipped[0].reason, 'No workstreams');
});

test('missing-report explanations distinguish expected report types and unknown save failures', () => {
 assert.match(missingReportExplanation({ kind: 'analysis', status: 'running' }), /still in progress/);
 assert.match(missingReportExplanation({ kind: 'event', status: 'done' }), /event report/);
 assert.match(missingReportExplanation({ kind: 'whatif', status: 'done' }), /scenario/);
 assert.match(missingReportExplanation({ kind: 'analysis', status: 'failed' }), /errors and messages/);
 assert.doesNotMatch(missingReportExplanation({ kind: 'analysis', status: 'done' }), /successfully saved/);
});
