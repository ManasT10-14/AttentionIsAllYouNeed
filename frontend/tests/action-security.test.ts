import test from 'node:test';
import assert from 'node:assert/strict';
import { actionSecurity } from '../src/lib/action-security';

const now = Date.parse('2026-10-26T12:00:00Z');
const valid = {
 id: 'a1', kind: 'breach_notice', status: 'approved',
 approval: { id: 'approval1', action_id: 'a1', tool: 'send_gmail', action_revision: 'revision', payload_hash: 'hash',
 expires_at: '2026-10-26T13:00:00Z', sources: [{ contract_id: 'C1', version: 2, sha256: 'source-hash' }] },
 approval_execution: {},
};

test('legacy approvals require fresh review and remain editable', () => {
 const state = actionSecurity({ id: 'a1', kind: 'breach_notice', status: 'approved' }, now);
 assert.equal(state.canExecute, false);
 assert.equal(state.canReview, true);
 assert.match(state.reason, /binding|review/i);
});

test('expiry uses wall clock and includes the exact expiry boundary', () => {
 assert.equal(actionSecurity(valid, now).canExecute, true);
 const expired = actionSecurity(valid, Date.parse('2026-10-26T13:00:00Z'));
 assert.equal(expired.canExecute, false);
 assert.equal(expired.canReview, true);
 assert.match(expired.reason, /expired/i);
});

test('consumed and ambiguous approvals cannot be sent, edited or reapproved', () => {
 for (const state of ['executing', 'completed', 'ambiguous', 'cancelled']) {
  const result = actionSecurity({ ...valid, approval_execution: { state } }, now);
  assert.equal(result.canExecute, false);
  assert.equal(result.canReview, false);
 }
});

test('wrong tools, incomplete sources and malformed expiry never allow execution', () => {
 for (const changes of [{ tool: 'apply_amendment' }, { sources: [] }, { expires_at: 'invalid' }, { action_id: 'other' }]) {
  assert.equal(actionSecurity({ ...valid, approval: { ...valid.approval, ...changes } }, now).canExecute, false);
 }
});

