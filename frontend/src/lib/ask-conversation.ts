import { text, type ApiRecord } from './api';
export type AskMessage = { question: string; answer: ApiRecord };
export function askHistory(messages: AskMessage[]) {
 return messages.filter(m => m.answer.status !== 'unanswered' && m.answer.insufficient_evidence !== true).slice(-4).map(m => ({ question: m.question.slice(0, 4000), contract_ids: Array.isArray(m.answer.scope_ids) ? m.answer.scope_ids.filter((id): id is string => typeof id === 'string') : [] }));
}
export function askReason(answer: ApiRecord): string {
 const reasons: Record<string, string> = { invalid_scope: 'Choose an available agreement and try again.', no_contracts: 'Upload a contract to start asking questions.', no_evidence: 'No matching clause evidence was found.', citation_failure: 'The answer could not be verified against the contracts.', provider_failure: 'The answer service could not finish. You can inspect the retrieved passages or retry.', budget_exceeded: 'The analysis reached its budget. Try a narrower question.' };
 return reasons[text(answer.reason, '')] ?? (answer.insufficient_evidence === true ? 'More evidence is needed to answer this question.' : '');
}
