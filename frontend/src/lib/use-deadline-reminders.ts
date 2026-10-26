'use client';
import { useEffect } from 'react';
import { list, type ApiRecord } from '@/lib/api';
import { upcomingDeadlineNotices, type Notice } from '@/lib/notifications';

export function useDeadlineReminders({ enabled, scope, asOf, preview, request, onRestore, onNew, onError }: {
 enabled: boolean; scope: string; asOf: string; preview: boolean;
 request: <T = unknown>(path: string, options?: RequestInit) => Promise<T>;
 onRestore: (notices: Notice[]) => void; onNew: (notices: Notice[]) => void; onError: (message: string) => void;
}) {
 useEffect(() => {
  if (!enabled) return;
  let active = true, busy = false; let epoch = 0; const abort = new AbortController();
  const storageKey = `odin:deadlines:${encodeURIComponent(scope)}:${asOf}`;
  let seen = new Set<string>(); let saved: Notice[] = [];
  try {
   const cached = JSON.parse(sessionStorage.getItem(storageKey) || '{}');
   seen = new Set(Array.isArray(cached.seen) ? cached.seen.filter((k: unknown): k is string => typeof k === 'string') : []);
   saved = Array.isArray(cached.notices) ? cached.notices.filter((n: Notice) => n && typeof n.id === 'number' && typeof n.title === 'string' && typeof n.href === 'string' && n.href.startsWith('/dashboard/') && n.category === 'deadline' && n.asOf === asOf).slice(0, 40).map((n: Notice) => ({ ...n, toast: false })) : [];
  } catch { /* Reminders also work when browser storage is unavailable. */ }
  onRestore(saved); onError('');
  const persist = () => { try { sessionStorage.setItem(storageKey, JSON.stringify({ seen: [...seen].slice(-400), notices: saved })); } catch { /* Keep the in-memory feed. */ } };
  async function check() {
   if (busy || !active) return;
   busy = true; const requestedEpoch = epoch;
   try {
    const response = await request<unknown>('/api/alerts?as_of=' + encodeURIComponent(asOf), { signal: abort.signal });
    if (!Array.isArray(response)) throw new Error('The deadline alert list was not returned.');
    if (!active || requestedEpoch !== epoch) return;
    const candidates = upcomingDeadlineNotices(list(response) as ApiRecord[], asOf, new Set(), Date.now(), preview);
    const activeKeys = new Set(candidates.map(n => n.key));
    const retained = saved.filter(n => activeKeys.has(n.key));
    const removed = retained.length !== saved.length; saved = retained;
    const fresh = candidates.filter(n => n.key && !seen.has(n.key));
    onError('');
    if (fresh.length) {
     fresh.forEach(n => { if (n.key) seen.add(n.key); });
     saved = [...fresh, ...saved].slice(0, 40); persist(); if (removed) onRestore(saved.map(n => ({ ...n, toast: false }))); onNew(fresh);
    }
    if (removed && !fresh.length) { persist(); onRestore(saved); }
   } catch (cause) { if (active && !abort.signal.aborted) onError(cause instanceof Error ? cause.message : 'Deadline reminders could not be refreshed.'); }
   finally { busy = false; if (active && requestedEpoch !== epoch) void check(); }
  }
  const dismiss = (event: Event) => { const id = (event as CustomEvent<number>).detail; saved = saved.filter(n => n.id !== id); persist(); };
  const deleted = (event: Event) => {
   const cid = (event as CustomEvent<string>).detail;
   if (!cid) return;
   epoch += 1;
   const removed = saved.filter(n => new URLSearchParams(n.href.split('?')[1] || '').get('contract_id') === cid);
   const removedKeys = new Set(removed.map(n => n.key));
   saved = saved.filter(n => !removedKeys.has(n.key));
   removed.forEach(n => { if (n.key) seen.delete(n.key); });
   persist(); onRestore(saved); void check();
  };
  const refresh = () => { void check(); };
  void check();
  const poll = setInterval(refresh, 60000);
  window.addEventListener('odin-deadline-refresh', refresh);
  window.addEventListener('odin-notice-dismiss', dismiss);
  window.addEventListener('odin-contract-deleted', deleted);
  return () => { active = false; abort.abort(); clearInterval(poll); window.removeEventListener('odin-deadline-refresh', refresh); window.removeEventListener('odin-notice-dismiss', dismiss); window.removeEventListener('odin-contract-deleted', deleted); };
 }, [enabled, scope, asOf, preview, request, onRestore, onNew, onError]);
}
