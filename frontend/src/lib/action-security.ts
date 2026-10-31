import { deliveryOperation, list, record, text } from './api';

export function validActionRecipients(value: string) {
 if (/[\r\n\0]/.test(value)) return false;
 const addresses = value.match(/[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}/g);
 return Boolean(addresses?.length);
}

/** A client preflight only. The server rechecks payload hashes and current sources. */
export function actionSecurity(value: unknown, wallClockMs = Date.now()) {
 const action = record(value);
 const binding = record(action.approval);
 const execution = text(record(action.approval_execution).state, '');
 const canReview = ['draft', 'approved'].includes(text(action.status, '')) && !execution;
 const operation = deliveryOperation(action.kind);
 const expectedTool = operation === 'apply' ? 'apply_amendment' : operation === 'send' ? 'send_gmail' : '';
 const sources = list(binding.sources);
 const expiry = text(binding.expires_at, '');
 const expiresAt = /(?:Z|[+-]\d{2}:\d{2})$/.test(expiry) ? Date.parse(expiry) : NaN;
 let reason = '';
 if (execution) reason = execution === 'executing' ? 'Execution is already claimed. Wait for the recorded outcome.' : 'Approval is consumed. Inspect the recorded outcome before creating another action.';
 else if (action.status !== 'approved') reason = 'A fresh review and approval are required before execution.';
 else if (!expectedTool) reason = 'Execution is unavailable for this action type.';
 else if (!binding.id || binding.action_id !== action.id || binding.tool !== expectedTool || !binding.payload_hash || !binding.action_revision || !sources.length || sources.some(source => !source.contract_id || !Number.isInteger(source.version) || Number(source.version) < 1 || !source.sha256)) reason = 'Approval binding or source versions are missing. Review and approve this action again.';
 else if (!Number.isFinite(expiresAt)) reason = 'Approval expiry is unavailable. Review and approve this action again.';
 else if (expiresAt <= wallClockMs) reason = 'Approval has expired. Review and approve this action again.';
 return { canExecute: !reason, canReview, reason, execution: execution || 'not claimed', binding, sources, expiresAt };
}
