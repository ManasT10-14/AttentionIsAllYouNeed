'use client';
import { CalendarDays, RotateCcw } from 'lucide-react';
import { dateText, daysBetween, offsetDate } from '@/lib/api';
import { useWorkspace } from './providers';
import { Button } from './ui';
export function ClockControl() {
 const w = useWorkspace(); const staged = !w.demo && w.clockBounds; const anchor = staged ? staged.start : w.realToday;
 const min = staged ? 0 : -60; const max = staged ? daysBetween(anchor, staged.end) : 365;
 const offset = Math.min(max,Math.max(min,daysBetween(anchor,w.date)));
 return <div className="simulation-clock live-clock"><div className="clock-date"><span><CalendarDays size={14} />SIMULATED DATE</span><strong>{dateText(w.date)}</strong><small>Preview while dragging · replay on release</small></div><div className="clock-track"><input type="range" aria-label="Simulated date" min={min} max={max} value={offset} disabled={w.clockPending || !w.canAdmin} onChange={e => w.setDate(offsetDate(anchor,Number(e.target.value)))} onPointerUp={() => void w.commitClock(w.date)} onKeyUp={e => { if (['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','PageUp','PageDown'].includes(e.key)) void w.commitClock(w.date); }} /><div className="clock-limits"><span>{staged ? dateText(staged.start) : "−60 days"}</span><span>{offset >= 0 ? '+' : ''}{offset} days</span><span>{staged ? dateText(staged.end) : "+365 days"}</span></div></div><div className="clock-shortcuts"><Button variant="secondary" disabled={w.clockPending || !w.canAdmin} onClick={() => void w.commitClock(staged && offsetDate(w.date,7) > staged.end ? staged.end : offsetDate(w.date,7))}>+1 week</Button><Button variant="ghost" disabled={w.clockPending || !w.canAdmin} onClick={() => staged ? w.setDate(w.clockNow) : void w.commitClock(anchor)}><RotateCcw size={13} />{staged ? "Current" : "Today"}</Button></div>{w.clockPending && <span role="status">Updating clock…</span>}{w.clockError && <p className="form-error" role="alert">{w.clockError}</p>}</div>;
}
