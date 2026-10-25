const datedViews = new Set(['/api/dashboard','/api/timeline','/api/alerts','/api/exposure','/api/heatmap']);
/** Only date previews may reuse a snapshot. Entity/filter changes must clear it. */
export function resourceIdentity(path: string | null): string | null {
 if(!path)return null;
 const url=new URL(path,'https://odin.invalid');
 if(!datedViews.has(url.pathname))return path;
 url.searchParams.delete('as_of');url.searchParams.sort();
 return url.pathname+(url.searchParams.size?'?'+url.searchParams:'');
}
export function canReuseSnapshot(previous:string|null,next:string|null) {
 return Boolean(previous&&next&&resourceIdentity(previous)===resourceIdentity(next));
}
export function snapshotDate(path:string|null) { return path?new URL(path,'https://odin.invalid').searchParams.get('as_of')??undefined:undefined; }
