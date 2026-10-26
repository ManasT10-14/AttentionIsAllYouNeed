import test from 'node:test';
import assert from 'node:assert/strict';
import { securityReviewRequest, securityReviewFeedback } from '../src/lib/security-review';

test('review requires an explanation and sends the observed revision', () => {
 assert.throws(() => securityReviewRequest('release', '  ', 0), /reason/i);
 assert.deepEqual(securityReviewRequest('dismiss', ' Reviewed evidence ', 3), { decision: 'dismiss', note: 'Reviewed evidence', expected_revision: 3 });
});

test('a failed release is surfaced as an error without a success claim', () => {
 const result = securityReviewFeedback({ status: 'release_failed', error: 'Manual recovery required' });
 assert.equal(result.error, true);
 assert.match(result.message, /Manual recovery/);
 assert.equal(result.runId, '');
});

test('release receipts show the launched run and dismiss states its limited effect', () => {
 assert.equal(securityReviewFeedback({ status: 'released', run_id: 'run-123' }).runId, 'run-123');
 assert.match(securityReviewFeedback({ status: 'dismissed' }).message, /remains held/i);
 assert.match(securityReviewFeedback({ status: 'release_pending' }).message, /pending/i);
});
