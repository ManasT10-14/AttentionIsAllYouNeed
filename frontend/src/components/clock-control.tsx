'use client';
import { CalendarDays, RotateCcw } from 'lucide-react';
import { dateText, daysBetween, offsetDate } from '@/lib/api';
import { useWorkspace } from './providers';
import { Button } from './ui';
export function ClockControl() {
 const w = useWorkspace(); const anchor = w.realToday;
 const offset = Math.min(365,Math.max(-60,daysBetween(anchor,w.date)));
 return <div className="simulation-clock live-clock"><div className="clock-date"><span><CalendarDays size={14} />SIMULATED DATE</span><strong>{dateText(w.date)}</strong><small>Preview while dragging · commit on release</small></div><div className="clock-track"><input type="range" aria-label="Simulated date" min={-60} max={365} value={offset} disabled={w.clockPending} onChange={e => w.setDate(offsetDate(anchor,Number(e.target.value)))} onPointerUp={() => void w.commitClock(w.date)} onKeyUp={e => { if (['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','PageUp','PageDown'].includes(e.key)) void w.commitClock(w.date); }} /><div className="clock-limits"><span>−60 days</span><span>{offset >= 0 ? '+' : ''}{offset} days</span><span>+365 days</span></div></div><div className="clock-shortcuts"><Button variant="secondary" disabled={w.clockPending} onClick={() => void w.commitClock(offsetDate(w.date,7))}>+1 week</Button><Button variant="ghost" disabled={w.clockPending} onClick={() => void w.commitClock(anchor)}><RotateCcw size={13} />Today</Button></div>{w.clockPending && <span role="status">Updating clock…</span>}{w.clockError && <p className="form-error" role="alert">{w.clockError}</p>}</div>;
}
