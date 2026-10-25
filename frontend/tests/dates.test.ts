import test from 'node:test';
import assert from 'node:assert/strict';
process.env.NEXT_PUBLIC_API_BASE_URL = '/';
const client = import('../src/lib/api');

test('dateText never shifts the calendar day and keeps one format', async () => {
  const { dateText } = await client;
  assert.equal(dateText('2026-11-02'), '2 Nov 2026');
  assert.equal(dateText('2026-11-02T03:00:00+05:30'), '2 Nov 2026');
  assert.equal(dateText('2026-10-25T00:30:00.123456'), '25 Oct 2026');
  assert.equal(dateText(undefined), 'Not provided');
});
test('dateTimeText keeps wall-clock time and offset', async () => {
  const { dateTimeText } = await client;
  assert.equal(dateTimeText('2026-11-02T03:00:00+05:30'), '2 Nov 2026, 03:00 +05:30');
  assert.equal(dateTimeText('2026-10-25T09:23:14.888986'), '25 Oct 2026, 09:23 UTC');
  assert.equal(dateTimeText('2026-11-02'), '2 Nov 2026');
});
test('wordDiff marks removed and added words', async () => {
  const { wordDiff } = await import('../src/lib/word-diff');
  const d = wordDiff('pay within 30 days', 'pay within 45 days');
  assert.deepEqual(d.filter(p => p.k === '-').map(p => p.t), ['30']);
  assert.deepEqual(d.filter(p => p.k === '+').map(p => p.t), ['45']);
});
