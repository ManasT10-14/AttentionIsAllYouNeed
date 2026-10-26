import test from 'node:test';
import assert from 'node:assert/strict';
process.env.NEXT_PUBLIC_API_BASE_URL = 'https://backend.example.test';
const client = import('../src/lib/api');
test('API client sends cookies and JSON to the configured backend, without local proxy routes',async()=>{
 const {api,apiUrl}=await client;const original=globalThis.fetch;let captured:RequestInit|undefined;let address='';
 globalThis.fetch=async(url,init)=>{address=String(url);captured=init;return Response.json({ok:true});};
 try{await api('/api/actions/a1/approve',{method:'POST',body:JSON.stringify({reviewed:true})});assert.equal(address,'https://backend.example.test/api/actions/a1/approve');assert.equal(captured?.credentials,'include');assert.equal(new Headers(captured?.headers).get('Content-Type'),'application/json');assert.throws(()=>apiUrl('https://untrusted.test/api/actions'));}finally{globalThis.fetch=original;}
});
test('failed requests surface the backend error and never return preview data',async()=>{
 const {api,ApiError}=await client;const original=globalThis.fetch;
 globalThis.fetch=async()=>Response.json({detail:'Not approved'},{status:403});
 try{await assert.rejects(()=>api('/api/actions/a1/send',{method:'POST'}),(error:unknown)=>error instanceof ApiError&&error.status===403&&error.message==='Not approved');}finally{globalThis.fetch=original;}
});
test('uploads preserve FormData boundaries and file field names',async()=>{
 const {api}=await client;const original=globalThis.fetch;let captured:RequestInit|undefined;
 globalThis.fetch=async(_url,init)=>{captured=init;return Response.json({results:[],run_ids:[]});};
 try{const files=new FormData();files.append('files',new Blob(['sample'],{type:'application/pdf'}),'contract.pdf');await api('/api/contracts?analyze=true',{method:'POST',body:files});assert.equal(captured?.body,files);assert.equal(new Headers(captured?.headers).has('Content-Type'),false);}finally{globalThis.fetch=original;}
});
test('money respects INR grouping and does not invent missing currencies or values',async()=>{
 const {formatMoney}=await client;assert.match(formatMoney({amount:450000,currency:'INR'}),/4,50,000/);assert.equal(formatMoney(undefined,'INR'),'Not provided');assert.equal(formatMoney(50),'Not provided');assert.match(formatMoney(0,'INR'),/0/);
});
test('graph rejects dangling edges and dashboard rejects malformed heatmap amounts',async()=>{
 const {validatePayload}=await client;
 assert.throws(()=>validatePayload('/api/graph',{nodes:[{id:'a',type:'contract',label:'A'}],edges:[{source:'a',target:'missing',kind:'depends_on'}]}));
 assert.throws(()=>validatePayload('/api/dashboard',{heatmap:{cells:[{contract_id:'a',clause_type:'payment',month:'2026-10',amount:'wrong'}]}}));
 assert.doesNotThrow(()=>validatePayload('/api/dashboard',{exposure:{expected:0,worst_case:0,currency:'INR',contracts:[]},heatmap:{cells:[]},alerts:[]}));
});
test('citations preserve version deep links and validate PDF highlight coordinates',async()=>{
 const {viewerLink,validatePayload}=await client;assert.equal(viewerLink({contract_id:'c 1',clause_number:'12.2',version:3}),'/viewer?contract=c+1&clause=12.2&v=3');
 assert.throws(()=>validatePayload('/api/citation/resolve',{page:1,text:'Clause',bboxes:[[1,0,0]]}));
 assert.doesNotThrow(()=>validatePayload('/api/citation/resolve',{page:1,text:'Clause',bboxes:[[1,20,30,200,80]],pdf_url:'/api/example'}));
});
test('preview fixtures are explicitly separate and cannot send email',async()=>{
 const {demoRequest}=await import('../src/lib/demo-api');const {validatePayload}=await client;
 for(const path of ['/api/contracts','/api/dashboard','/api/graph','/api/timeline','/api/debate','/api/actions'])validatePayload(path,await demoRequest(path));
 await assert.rejects(()=>demoRequest('/api/actions/a1/send',{method:'POST'}),/needs the connected backend/);
});

test('auth uses nested logged-out flags and company.sim_now',async()=>{
 const {loggedOutFlags,parseSession}=await client;
 assert.deepEqual(loggedOutFlags({detail:{error:'not logged in',google_configured:true,dev_login:false}}),{error:'not logged in',google_configured:true,dev_login:false});
 const session=parseSession({user:{id:'u1',email:'a@example.test',role:'admin'},company:{id:'c1',name:'Example',sim_now:'2026-11-15'}});
 assert.equal(session.company?.sim_now,'2026-11-15');
});
test('email template is returned as plain text without JSON parsing',async()=>{
 const {api}=await client;const original=globalThis.fetch;
 globalThis.fetch=async()=>new Response('Subject: Payment\nContract: C-1',{headers:{'Content-Type':'text/plain'}});
 try{assert.equal(await api('/api/email/template'),'Subject: Payment\nContract: C-1');}finally{globalThis.fetch=original;}
});
test('clock GET checks date-only fields and accepts backend real_today',async()=>{
 const {validatePayload,isIsoDate}=await client;
 assert.equal(isIsoDate('2026-02-30'),false);
 assert.equal(isIsoDate('2026-10-25T00:00:00Z'),false);
 assert.doesNotThrow(()=>validatePayload('/api/clock',{sim_now:'2026-11-15',real_today:'2026-10-25'}));
 assert.throws(()=>validatePayload('/api/clock',{sim_now:'2026-11-15'}));
});
test('all unnamed record kinds invalidate views except ping',async()=>{
 const {shouldRefresh}=await client;
 for(const kind of ['timeline','dependency','finding','clock','agent_message','new_record_type'])assert.equal(shouldRefresh(kind),true);
 assert.equal(shouldRefresh('ping'),false);assert.equal(shouldRefresh(undefined),false);
});
test('cascade paths map raw contract ids to c: graph ids',async()=>{
 const {cascadeNodeIds}=await client;
 assert.deepEqual([...cascadeNodeIds({nodes:[],edges:[],cascades:{one:['two','three']}},'one')],['c:one','c:two','c:three']);
});
test('timeline type lookup joins citation clause numbers instead of deadline kinds',async()=>{
 const {indexClauseTypes,clauseTypeKey}=await client;
 const index=indexClauseTypes([{id:'c1',clauses:[{number:'12.2',clause_type:'Renewal'},{number:'8.4',clause_type:'Payment'}]}]);
 assert.equal(index[clauseTypeKey('c1','12.2')],'renewal');assert.equal(index[clauseTypeKey('c1','8.4')],'payment');
});
test('only amendment applies; other confirmed action kinds send',async()=>{
 const {deliveryOperation,actionKinds,validRecipient}=await client;
 for(const kind of actionKinds)assert.equal(deliveryOperation(kind),kind==='amendment'?'apply':'send');
 assert.equal(deliveryOperation('unknown_amendment_type'),null);assert.equal(validRecipient('Name or department'),false);assert.equal(validRecipient('legal@example.test'),true);
});
test('development proxy preserves the static frontend and handles callback before page routing',async()=>{
 const config=(await import('../next.config')).default;
 const dev=config('phase-development-server');const prod=config('phase-production-build');
 assert.equal(dev.output,undefined);assert.equal(dev.skipTrailingSlashRedirect,true);assert.equal(prod.output,'export');assert.equal(prod.rewrites,undefined);
 const rewrites=await dev.rewrites!();
 assert.ok(!Array.isArray(rewrites)&&rewrites.beforeFiles?.some(rule=>rule.source==='/api/:path*'));
 assert.ok(!Array.isArray(rewrites)&&rewrites.beforeFiles?.some(rule=>rule.source==='/auth/google/callback'));
});

test('Ask gets a longer timeout while other requests retain the default and caller abort still works', async () => {
 const { api } = await client;
 const originalFetch = globalThis.fetch; const originalTimeout = AbortSignal.timeout;
 const deadlines: number[] = []; const caller = new AbortController();
 AbortSignal.timeout = (ms: number) => { deadlines.push(ms); return new AbortController().signal; };
 globalThis.fetch = async (_url, init) => {
  assert.ok(init?.signal);
  if (String(_url).endsWith('/api/ask')) { caller.abort(); assert.equal(init?.signal?.aborted, true); }
  return Response.json({ answer: 'stubbed' });
 };
 try {
  await api('/api/ask', { method: 'POST', signal: caller.signal });
  await api('/api/actions/test', { method: 'POST' });
  assert.deepEqual(deadlines, [240000, 30000]);
 } finally { globalThis.fetch = originalFetch; AbortSignal.timeout = originalTimeout; }
});

test('compiled local mode retains API and auth proxy without static export or route compilation', async () => {
 const previous = process.env.ODIN_LOCAL_SERVER;
 try {
  process.env.ODIN_LOCAL_SERVER = '1';
  const config = (await import('../next.config')).default('phase-production-build');
  assert.equal(config.output, undefined);
  assert.equal(config.distDir, '.next-local');
  assert.equal(config.compress, false);
  const rules = await config.rewrites!();
  assert.ok(!Array.isArray(rules) && rules.beforeFiles?.some(r => r.source === '/api/:path*'));
  assert.ok(!Array.isArray(rules) && rules.beforeFiles?.some(r => r.source === '/auth/google/callback'));
 } finally { if (previous === undefined) delete process.env.ODIN_LOCAL_SERVER; else process.env.ODIN_LOCAL_SERVER = previous; }
});
