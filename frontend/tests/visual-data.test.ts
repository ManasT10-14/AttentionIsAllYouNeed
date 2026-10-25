import test from 'node:test';
import assert from 'node:assert/strict';
import {heatScaleMaximum,heatLevel} from '../src/lib/heatmap';
import {layoutGraph} from '../src/lib/graph-layout';
test('heatmap scale uses aggregated monthly cells instead of an individual clause maximum',()=>{
 const cells=[{contract_id:'a',clause_type:'payment',month:'2026-11',amount:100},{contract_id:'a',clause_type:'renewal',month:'2026-11',amount:200},{contract_id:'b',clause_type:'payment',month:'2026-11',amount:250}];
 assert.equal(heatScaleMaximum(cells,'contract'),300);
 assert.equal(heatScaleMaximum(cells,'type'),350);
 assert.equal(heatLevel(0,300),0);assert.equal(heatLevel(300,300),4);
});
test('connected party, agreement and clauses occupy distinct left-to-right ranks',()=>{
 const result=layoutGraph({nodes:[{id:'p',type:'party',label:'Party'},{id:'c',type:'contract',label:'Contract'},{id:'cl',type:'clause',label:'Clause'}],edges:[{source:'p',target:'c',kind:'party_to'},{source:'c',target:'cl',kind:'contains'}]});
 assert.ok(result[0].position.x<result[1].position.x);assert.ok(result[1].position.x<result[2].position.x);
 assert.ok(result.every(n=>Number.isFinite(n.position.x)&&Number.isFinite(n.position.y)));
});
