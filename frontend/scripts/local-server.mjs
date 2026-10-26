// Precompile all routes, then use Next's supported production server and existing API proxy.
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
const next = fileURLToPath(new URL('../node_modules/next/dist/bin/next', import.meta.url));
const env = { ...process.env, ODIN_LOCAL_SERVER: '1', NEXT_PUBLIC_API_BASE_URL: '/' };
let child;
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => { child?.kill(signal); });
function run(args) {
 return new Promise((resolve, reject) => {
  child = spawn(process.execPath, [next, ...args], {cwd: root, env, stdio: 'inherit', windowsHide: true});
  child.once('error', reject);
  child.once('exit', (code, signal) => resolve(signal ? 1 : code ?? 1));
 });
}
console.log('Building local production UI. Routes compile once before the server starts.');
const build = await run(['build', '--webpack']);
if (build !== 0) process.exit(build);
console.log('Starting compiled UI at http://127.0.0.1:3000 with the backend proxy enabled.');
process.exit(await run(['start', '--hostname', '127.0.0.1', '--port', '3000']));
