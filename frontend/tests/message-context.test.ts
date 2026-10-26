import test from 'node:test';
import assert from 'node:assert/strict';
import { availableMessageResult, enrichWorkflowSteps, nextReplayIndex, relatedMessageFindings } from '../src/lib/message-context';

test('replay advances only through captured steps and stops at the end', () => {
 assert.equal(nextReplayIndex(0, 3), 1);
 assert.equal(nextReplayIndex(2, 3), null);
 assert.equal(nextReplayIndex(-1, 0), null);
 assert.equal(nextReplayIndex(0, 1), null);
});
test('workflow enrichment joins exact message IDs and preserves timeline intervals', () => {
 const result = enrichWorkflowSteps([{ id: 'a', duration_s: 2, tool_calls: [{ tool: 'read' }] }, { id: 'b' }], [{ id: 'a', run_id: 'run', payload: { finding_id: 'f1' }, duration_s: 99 }, { id: 'c', payload: { unrelated: true } }]);
 assert.equal(result[0].duration_s, 2);
 assert.equal(result[0].run_id, 'run');
 assert.deepEqual(result[0].payload, { finding_id: 'f1' });
 assert.deepEqual(result[1], { id: 'b' });
});
test('message evidence includes only explicitly referenced findings and reports missing records', () => {
 const result = relatedMessageFindings({ payload: { finding_id: 'a', finding_ids: ['a', 'missing'], disputed: ['b'] } }, { findings: [{ id: 'a' }, { id: 'unrelated' }], debate: [{ finding: { id: 'b' } }] });
 assert.deepEqual(result.requested, ['a', 'missing', 'b']);
 assert.deepEqual(result.found.map(f => f.id), ['a', 'b']);
 assert.deepEqual(result.missing, ['missing']);
 assert.deepEqual(relatedMessageFindings({ contract_id: 'same' }, { findings: [{ id: 'f', contract_id: 'same' }] }).found, []);
});

test('message fallback reuses referenced evidence when enrichment is unavailable', () => {
 const message = {sender: 'heimdall', payload: {finding_ids: ['f']}};
 const result = availableMessageResult(message, {findings: [{id: 'f', claim: 'Saved claim'}, {id: 'other'}], verifications: [{finding_id: 'f', rationale: 'Clause supports it'}, {finding_id: 'other'}]});
 const sections = result.sections as {title: string; value: unknown[]}[];
 assert.equal(result.source, 'available_records');
 assert.equal(sections[0].value.length, 1);
 assert.equal(sections[1].value.length, 1);
});
test('saved Synth report payload is readable without an enrichment endpoint', () => {
 const result = availableMessageResult({sender: 'synth', payload: {result_snapshot: {summary: {executive_summary: 'Saved conclusion'}, conflicts: [{claim: 'Forum issue'}]}}}, {});
 assert.equal(result.source, 'message_time_snapshot');
 assert.equal((result.sections as unknown[]).length, 2);
});
test('message fallback never assigns unrelated findings to a sparse legacy message', () => {
 assert.deepEqual(availableMessageResult({sender: 'synth', payload: {completeness: 'complete'}}, {findings: [{id: 'unrelated', claim: 'Not referenced'}]}).sections, []);
});
