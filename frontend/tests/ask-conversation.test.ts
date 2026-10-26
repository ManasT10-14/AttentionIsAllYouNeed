import test from 'node:test';
import assert from 'node:assert/strict';
import { askHistory, askReason } from '../src/lib/ask-conversation';

test('follow-up context carries only recent user questions and successful agreement scopes', () => {
 const turns = Array.from({ length: 6 }, (_, i) => ({ question: `Question ${i}`, answer: { status: 'answered', scope_ids: [`TEST-${i}`], answer: 'Generated answer must not be sent as evidence' } }));
 turns.push({ question: 'Failed turn', answer: { status: 'unanswered', scope_ids: [], answer: '' } });
 const history = askHistory(turns);
 assert.equal(history.length, 4);
 assert.deepEqual(history[0], { question: 'Question 2', contract_ids: ['TEST-2'] });
 assert.equal(JSON.stringify(history).includes('Generated answer'), false);
 assert.equal(JSON.stringify(history).includes('Failed turn'), false);
});
test('Ask failure messages distinguish missing evidence from service failures', () => {
 assert.match(askReason({ reason: 'provider_failure' }), /service/);
 assert.match(askReason({ reason: 'no_evidence' }), /clause evidence/);
 assert.match(askReason({ reason: 'invalid_scope' }), /agreement/);
 assert.equal(askReason({ status: 'answered' }), '');
});
