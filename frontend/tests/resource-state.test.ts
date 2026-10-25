import test from 'node:test';
import assert from 'node:assert/strict';
import {canReuseSnapshot,resourceIdentity,snapshotDate} from '../src/lib/resource-state';
test('dragging the clock preserves the same dashboard snapshot until new data arrives',()=>{
 assert.equal(canReuseSnapshot('/api/dashboard?as_of=2026-10-25','/api/dashboard?as_of=2026-11-05'),true);
 assert.equal(snapshotDate('/api/dashboard?as_of=2026-10-25'),'2026-10-25');
});
test('timeline dates may reuse rows, but switching contracts must never show old entity data',()=>{
 assert.equal(canReuseSnapshot('/api/timeline?as_of=2026-10-25&contract_id=a','/api/timeline?contract_id=a&as_of=2026-11-05'),true);
 assert.equal(canReuseSnapshot('/api/timeline?contract_id=a&as_of=2026-10-25','/api/timeline?contract_id=b&as_of=2026-11-05'),false);
});
test('action review, selected contracts and closed-alert filters remain isolated',()=>{
 assert.equal(canReuseSnapshot('/api/actions/a1','/api/actions/a2'),false);
 assert.equal(canReuseSnapshot('/api/contracts/a','/api/contracts/b'),false);
 assert.equal(canReuseSnapshot('/api/alerts?include_closed=false&as_of=2026-10-25','/api/alerts?include_closed=true&as_of=2026-11-05'),false);
 assert.equal(canReuseSnapshot(null,'/api/dashboard'),false);
 assert.equal(resourceIdentity('/api/actions/a1?as_of=2026-10-25'),'/api/actions/a1?as_of=2026-10-25');
});
