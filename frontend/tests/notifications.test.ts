import test from 'node:test';
import assert from 'node:assert/strict';
import { upcomingDeadlineNotices } from '../src/lib/notifications';
const alert = { id: 'a1', kind: 'notice_deadline', status: 'open', contract_id: 'C01', title: 'Send renewal notice', due_date: '2026-11-02' };

test('deadline reminders cover today through seven days and exclude old or distant dates', () => {
 assert.equal(upcomingDeadlineNotices([alert], '2026-10-26', new Set(), 100)[0].title, 'Due in 7 days: Send renewal notice');
 assert.match(upcomingDeadlineNotices([alert], '2026-11-01', new Set(), 100)[0].title, /Due tomorrow/);
 assert.match(upcomingDeadlineNotices([alert], '2026-11-02', new Set(), 100)[0].title, /Due today/);
 assert.equal(upcomingDeadlineNotices([alert], '2026-11-03', new Set(), 100).length, 0);
 assert.equal(upcomingDeadlineNotices([alert], '2026-10-25', new Set(), 100).length, 0);
});

test('completed, snoozed, event-only, and malformed alerts do not create deadline reminders', () => {
 const items = [{ ...alert, status: 'resolved' }, { ...alert, status: 'acknowledged' }, { ...alert, status: 'snoozed' }, { ...alert, kind: 'event' }, { ...alert, due_date: '2026-02-30' }];
 assert.deepEqual(upcomingDeadlineNotices(items, '2026-10-26', new Set(), 100), []);
 assert.deepEqual(upcomingDeadlineNotices([alert], 'bad-date', new Set(), 100), []);
});

test('deduplication suppresses repeated polls and duplicate alerts without mutating seen keys', () => {
 const seen = new Set<string>();
 const first = upcomingDeadlineNotices([alert, alert], '2026-10-26', seen, 100);
 assert.equal(first.length, 1); assert.equal(seen.size, 0);
 const seenAfter = new Set([first[0].key!]);
 assert.equal(upcomingDeadlineNotices([alert], '2026-10-26', seenAfter, 100).length, 0);
 assert.equal(upcomingDeadlineNotices([alert], '2026-11-02', seenAfter, 100).length, 1);
});

test('reminders link to the affected agreement and clearly mark preview notifications', () => {
 const result = upcomingDeadlineNotices([alert], '2026-10-26', new Set(), 100, true)[0];
 assert.equal(result.href, '/dashboard/timeline?contract_id=C01&month=2026-11');
 assert.match(result.title, /^Sample/);
 assert.match(result.detail!, /workspace date 26 Oct 2026/);
 assert.equal(result.asOf, '2026-10-26');
});
