import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import openapiTS, { astToString } from 'openapi-typescript';
for (const file of ['.env','.env.local']) if (existsSync(file)) process.loadEnvFile(file);
const base = (process.env.NEXT_PUBLIC_API_BASE_URL ?? '').replace(/\/$/,'');
const backend = (process.env.API_PROXY_TARGET || 'http://localhost:8000').replace(/\/$/,'');
const source = process.env.OPENAPI_URL || (base && base !== '/' ? base : backend) + '/openapi.json';
if (!source || !/^https?:\/\//.test(source)) {
 console.error('Set OPENAPI_URL or an absolute NEXT_PUBLIC_API_BASE_URL, then run gen:api with the backend running.'); process.exit(1);
}
try {
 const schema = await openapiTS(new URL(source));
 mkdirSync('src/lib/generated',{recursive:true});
 writeFileSync('src/lib/generated/backend.d.ts',astToString(schema));
 console.log('Generated request types in src/lib/generated/backend.d.ts. Check response types against docs/api-samples; backend OpenAPI responses may be any.');
} catch(error) { console.error('Could not generate API types:',error instanceof Error ? error.message : error); process.exit(1); }
