import test from 'node:test';
import assert from 'node:assert/strict';
import { activityInstant, activityTimeText } from '../src/lib/activity-time';
import { agentHandoffs } from '../src/lib/agent-handoffs';

test('the screenshot UTC stamp converts to the following calendar day in India', () => {
 assert.equal(activityTimeText('2026-10-25T21:13:00', 'Asia/Kolkata'), '26 Oct 2026, 02:43:00 IST');
 assert.equal(activityTimeText('2026-10-25T21:13:00Z', 'UTC'), '25 Oct 2026, 21:13:00 UTC');
 assert.equal(activityTimeText('2026-10-26T02:43:00+05:30', 'Asia/Calcutta'), '26 Oct 2026, 02:43:00 IST');
});

test('activity parsing treats naive backend stamps as UTC without shifting contract dates', () => {
 assert.equal(activityInstant('2026-10-25T21:13:00.123456'), '2026-10-25T21:13:00.123Z');
 assert.equal(activityInstant('2026-10-25'), undefined);
 assert.equal(activityTimeText('2026-10-25', 'Asia/Kolkata'), '25 Oct 2026');
 assert.equal(activityTimeText('invalid', 'Asia/Kolkata'), 'Not provided');
 assert.equal(activityTimeText('2026-10-25T21:13:00Z', 'Invalid/Zone'), '25 Oct 2026, 21:13:00 UTC');
});

test('communication graph preserves direction, repeat handoffs, and message evidence', () => {
 const messages = [{ id: 'a', sender: 'Loki', receiver: 'Thor', summary: 'Clarify clause', kind: 'clarify', ts: '2026-10-25T21:00:00' }, { id: 'b', sender: 'Thor', receiver: 'Loki', summary: 'Extraction answer' }, { id: 'c', sender: 'loki', receiver: 'thor', summary: 'Another question' }];
 const graph = agentHandoffs(messages);
 assert.equal(graph.connections.length, 2);
 assert.deepEqual(graph.connections.find(c => c.source === 'loki')?.steps.map(s => s.id), ['a', 'c']);
 assert.equal(graph.connections.find(c => c.source === 'thor')?.target, 'loki');
 assert.equal(graph.steps[0].message.summary, 'Clarify clause');
 assert.equal(graph.steps[0].at, '2026-10-25T21:00:00.000Z');
 assert.deepEqual(messages.map(m => m.sender), ['Loki', 'Thor', 'loki']);
});

test('the graph never invents recipients or expands broadcast messages into fake exchanges', () => {
 const graph = agentHandoffs([{ sender: 'odin', receiver: 'all', id: 'plan' }, { sender: 'thor', id: 'missing-recipient' }]);
 assert.deepEqual(graph.agents, ['odin', 'all']);
 assert.equal(graph.connections.length, 1);
 assert.equal(graph.unrouted, 1);
 assert.equal(graph.steps.length, 2);
 assert.deepEqual(agentHandoffs([]).connections, []);
});
