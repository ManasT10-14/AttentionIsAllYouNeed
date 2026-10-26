'use client';

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { api, ApiError, apiConfigured, apiUrl, post, record, text, today, isIsoDate, parseSession, loggedOutFlags, shouldRefresh, type Session, type ApiRecord } from '@/lib/api';
import { isDeadlineAlert, type Notice } from '@/lib/notifications';
import { useDeadlineReminders } from '@/lib/use-deadline-reminders';
import { demoRequest, resetDemo } from '@/lib/demo-api';

type Workspace = {
  timeZone: string; demo: boolean; ready: boolean; session: Session | null; sessionError: string; authFlags: ApiRecord;
  clockBounds: {start: string; end: string} | null; clockNow: string;
  date: string; realToday: string; setDate: (date: string) => void; commitClock: (date: string) => Promise<void>; clockError: string; clockPending: boolean;
  revision: number; refresh: () => void; enterDemo: () => void; logout: () => Promise<void>; loadSession: () => Promise<void>;
  request: <T = unknown>(path: string, options?: RequestInit) => Promise<T>; canAdmin: boolean;
  deadlineError: string; connection: 'connecting' | 'live' | 'reconnecting' | 'offline' | 'demo' | 'unconfigured'; notices: Notice[];
  dismissNotice: (id: number) => void;
};
const Context = createContext<Workspace | null>(null);
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [timeZone, setTimeZone] = useState('UTC');
  const [demo, setDemo] = useState(false);
  const [ready, setReady] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [sessionError, setSessionError] = useState('');
  const [authFlags, setAuthFlags] = useState<ApiRecord>({});
  const [date, setDate] = useState(today);
  const [clockBounds, setClockBounds] = useState<{start: string; end: string} | null>(null);
  const [clockNow, setClockNow] = useState(today);
  const [realToday, setRealToday] = useState(today);
  const [clockError, setClockError] = useState('');
  const [clockPending, setClockPending] = useState(false);
  const [revision, setRevision] = useState(0);
  const [connection, setConnection] = useState<Workspace['connection']>('unconfigured');
  const [notices, setNotices] = useState<Notice[]>([]);
  const [deadlineError, setDeadlineError] = useState('');
  const [notificationDate, setNotificationDate] = useState(today);
  const committedDate = useRef(today());
  const clockBusy = useRef(false);
  const refresh = useCallback(() => setRevision(v => v + 1), []);
  const loadSession = useCallback(async () => {
    setSessionError('');
    if (!apiConfigured) { setReady(true); return; }
    try {
      const response = await api<unknown>('/api/auth/me');
      const value = parseSession(response);
      setSession(value);
      setAuthFlags(record(response));
      if (isIsoDate(value.company?.sim_now)) { setDate(value.company.sim_now); setNotificationDate(value.company.sim_now); committedDate.current = value.company.sim_now; }
      try {
        const clock = await api<{ sim_now: string; real_today: string; simulation?: {start_date: string; end_date: string} }>('/api/clock');
        setClockNow(clock.sim_now);
        setClockBounds(clock.simulation ? {start: clock.simulation.start_date, end: clock.simulation.end_date} : null);
        setDate(clock.sim_now); setNotificationDate(clock.sim_now); committedDate.current = clock.sim_now; setRealToday(clock.real_today); setClockError('');
      } catch (error) { setClockError(error instanceof Error ? error.message : 'Could not read the shared clock.'); }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) { setSession(null); setAuthFlags(loggedOutFlags(error.body)); }
      else setSessionError(error instanceof Error ? error.message : 'Could not check your session.');
    } finally { setReady(true); }
  }, []);
  useEffect(() => {
    setTimeZone(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
    if (sessionStorage.getItem('odin-demo') === 'true') { setDemo(true); setRealToday('2026-10-25'); setDate('2026-10-25'); setNotificationDate('2026-10-25'); committedDate.current = '2026-10-25'; setReady(true); }
    else void loadSession();
    const expired = () => { setSession(null); };
    window.addEventListener('odin-session-expired', expired);
    return () => window.removeEventListener('odin-session-expired', expired);
  }, [loadSession]);
  const request = useCallback(async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
    if (demo) return await demoRequest(path, options) as T;
    return api<T>(path, options);
  }, [demo]);
  const restoreDeadlines = useCallback((items: Notice[]) => setNotices(previous => [...previous.filter(n => n.category !== 'deadline'), ...items].slice(0, 40)), []);
  const addDeadlines = useCallback((items: Notice[]) => setNotices(previous => [...items, ...previous.filter(n => !items.some(item => item.key && item.key === n.key))].slice(0, 40)), []);
  useDeadlineReminders({ enabled: ready && Boolean(session || demo), scope: demo ? 'preview' : text(record(session?.company).id, session?.user.email ?? 'workspace'), asOf: notificationDate, preview: demo, request, onRestore: restoreDeadlines, onNew: addDeadlines, onError: setDeadlineError });
  async function commitClock(next: string) {
    if (clockBusy.current) return;
    clockBusy.current = true; setClockPending(true); setClockError('');
    try {
      const response = await request<ApiRecord>('/api/clock', { method: 'POST', body: JSON.stringify({ sim_now: next }) });
      if (!isIsoDate(response?.sim_now)) throw new Error('The backend returned an invalid committed date.');
      const confirmed = response.sim_now;
      setClockNow(confirmed);
      committedDate.current = confirmed; setDate(confirmed); setNotificationDate(confirmed); refresh();
    } catch (error) { setDate(committedDate.current); setClockError(error instanceof Error ? error.message : 'Could not update clock.'); }
    finally { clockBusy.current = false; setClockPending(false); }
  }
  useEffect(() => {
    if (demo) { setConnection('demo'); return; }
    if (!session || !apiConfigured) { setConnection('unconfigured'); return; }
    let lastMessage = Date.now();
    const runStatuses = new Map<string, string>();
    let debounce: ReturnType<typeof setTimeout> | undefined;
    const stream = new EventSource(apiUrl('/api/stream'), { withCredentials: true });
    setConnection('connecting');
    const receive = (event: MessageEvent) => {
      lastMessage = Date.now(); setConnection('live');
      try {
        const message = record(JSON.parse(event.data)); const kind = text(message.kind, ''); const data = record(message.data);
        if (kind === 'ping') return;
        if (shouldRefresh(kind)) {
          clearTimeout(debounce); debounce = setTimeout(refresh, 600);
          if (kind === 'clock' && isIsoDate(data.sim_now) && !clockBusy.current) { setClockNow(data.sim_now.slice(0,10)); setDate(data.sim_now.slice(0,10)); setNotificationDate(data.sim_now.slice(0,10)); committedDate.current = data.sim_now.slice(0,10); }
          const runKey = text(data.id ?? data.run_id, '');
          const runChanged = kind === 'run' && typeof data.status === 'string' && runStatuses.get(runKey) !== data.status;
          if (runChanged) runStatuses.set(runKey, String(data.status));
          if (kind === 'contract_deleted') window.dispatchEvent(new CustomEvent('odin-contract-deleted', {detail: text(data.contract_id, '')}));
          if (kind === 'alert' || kind === 'event' || kind === 'clock') window.dispatchEvent(new Event('odin-deadline-refresh'));
          if ((kind === 'alert' && !isDeadlineAlert(data) && ['high','critical'].includes(text(data.severity, ''))) || runChanged || kind === 'email') {
            const href = kind === 'alert' ? '/dashboard/actions' : kind === 'email' ? '/dashboard/events' : '/dashboard/observability';
            setNotices(previous => [{ id: Date.now() + Math.random(), title: text(data.title ?? data.summary, kind === 'run' ? 'Run status: ' + text(data.status) : 'New inbox activity'), href }, ...previous].slice(0, 40));
          }
        }
      } catch { /* Invalid frames do not replace validated REST data. */ }
    };
    stream.onmessage = receive;
    // Backend data uses unnamed envelopes; ping is a separate named heartbeat.
    stream.addEventListener('ping', () => { lastMessage = Date.now(); setConnection('live'); });
    stream.onopen = () => { lastMessage = Date.now(); setConnection('live'); };
    stream.onerror = () => setConnection(navigator.onLine ? 'reconnecting' : 'offline');
    const heartbeat = setInterval(() => { if (Date.now() - lastMessage > 45000) setConnection(navigator.onLine ? 'reconnecting' : 'offline'); }, 5000);
    const offline = () => setConnection('offline'); window.addEventListener('offline', offline);
    return () => { stream.close(); clearInterval(heartbeat); clearTimeout(debounce); window.removeEventListener('offline', offline); };
  }, [session, demo, refresh]);
  function enterDemo() { resetDemo(); sessionStorage.setItem('odin-demo','true'); setDemo(true); setSession(null); setSessionError(''); setDate('2026-10-25'); setRealToday('2026-10-25'); setNotificationDate('2026-10-25'); committedDate.current = '2026-10-25'; setReady(true); refresh(); }
  async function logout() {
    try { if (!demo) await post('/api/auth/logout'); sessionStorage.removeItem('odin-demo'); setDemo(false); setSession(null); window.location.assign('/auth/sign-in'); }
    catch (error) { setSessionError(error instanceof Error ? error.message : 'Sign-out failed.'); }
  }
  const dismissNotice = (id: number) => { setNotices(previous => previous.filter(n => n.id !== id)); window.dispatchEvent(new CustomEvent('odin-notice-dismiss', { detail: id })); };
  const canAdmin = demo || ['admin','super_admin'].includes(session?.user.role ?? '');
  return <Context.Provider value={{ clockBounds, clockNow, timeZone, demo, ready, session, sessionError, authFlags, date, realToday, setDate, commitClock, clockError, clockPending, revision, refresh, enterDemo, logout, loadSession, request, canAdmin, deadlineError, connection, notices, dismissNotice }}>{children}</Context.Provider>;
}
export function useWorkspace() { const value = useContext(Context); if (!value) throw new Error('WorkspaceProvider required'); return value; }
