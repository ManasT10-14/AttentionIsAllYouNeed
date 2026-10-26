import { record, text } from './api';

export function securityReviewRequest(decision: string, reason: string, revision: number) {
 const note = reason.trim();
 if (!note) throw new Error('A review reason is required.');
 return { decision, note, expected_revision: revision };
}

export function securityReviewFeedback(value: unknown) {
 const result = record(value);
 const status = text(result.status, 'unknown');
 const messages: Record<string, string> = {
  released: 'Release validated. Event processing launched.',
  release_pending: 'Release is pending validation or launch. Refresh for the result.',
  dismissed: 'Detection dismissed. Any quarantined event remains held.',
  confirmed: 'Injection confirmed. The held event was rejected.',
 };
 return { error: status === 'release_failed' || !messages[status],
  message: status === 'release_failed' ? text(result.error, 'Release failed. Manual recovery is required.') : messages[status] ?? 'Review outcome unavailable. Refresh before retrying.',
  runId: text(result.run_id, '') };
}
