export type Part = { t: string; k: '=' | '-' | '+' };
/** Word-level diff (LCS). Clause text is short, so O(n*m) is fine. */
export function wordDiff(before: string, after: string): Part[] {
  const a = before.split(/(\s+)/).filter(Boolean), b = after.split(/(\s+)/).filter(Boolean);
  const dp = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--) dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out: Part[] = []; let i = 0, j = 0;
  const push = (t: string, k: Part['k']) => { const last = out[out.length - 1]; if (last && last.k === k) last.t += t; else out.push({ t, k }); };
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { push(a[i], '='); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) push(a[i++], '-');
    else push(b[j++], '+');
  }
  while (i < a.length) push(a[i++], '-');
  while (j < b.length) push(b[j++], '+');
  return out;
}
