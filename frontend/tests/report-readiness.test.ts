import test from 'node:test';
import assert from 'node:assert/strict';
import { reportReadiness } from '../src/lib/report-readiness';
test('empty recovery placeholders are not treated as completed reports', () => {
 assert.equal(reportReadiness({kind: 'contract', key_terms: null, actions: [], timeline: [], summary_status: 'unavailable'}), 'analysis_missing');
});
test('saved evidence without generated prose requires synthesis rather than implying no analysis', () => {
 assert.equal(reportReadiness({kind: 'contract', key_terms: {payments: []}, summary: {unavailable: true}}), 'summary_missing');
});
test('a generated summary with saved analysis is ready', () => {
 assert.equal(reportReadiness({kind: 'contract', key_terms: {}, summary: {executive_summary: 'Saved conclusion'}}), 'ready');
});
