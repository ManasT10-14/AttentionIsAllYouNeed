// Preserve Next's dot-form segment URLs when Windows exports them as nested paths.
import { readdir,copyFile } from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('out');
let copied=0;
async function visit(directory) {
 for(const entry of await readdir(directory,{withFileTypes:true})) {
  const absolute=path.join(directory,entry.name);
  if(entry.isDirectory())await visit(absolute);
  else if(entry.name.endsWith('.txt')) {
   const parts=path.relative(root,absolute).split(path.sep);
   const segment=parts.findIndex(part=>part.startsWith('__next.'));
   if(segment>=0 && segment<parts.length-1) {
    const destination=path.join(root,...parts.slice(0,segment),parts.slice(segment).join('.'));
    await copyFile(absolute,destination);copied++;
   }
  }
 }
}
await visit(root);
console.log('Static export ready; normalized '+copied+' segment asset paths.');
