import { dateText, text } from './api';

/** Backend activity stamps without an offset are UTC; date-only contract values stay dates. */
export function activityInstant(value: unknown): string | undefined {
 const raw = text(value, '').trim();
 if (!/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(raw)) return undefined;
 const normalized = raw.replace(' ', 'T').replace(/(\.\d{3})\d+/, '$1');
 const iso = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(normalized) ? normalized : normalized + 'Z';
 return Number.isFinite(Date.parse(iso)) ? new Date(iso).toISOString() : undefined;
}
export function activityTimeText(value: unknown, timeZone = 'UTC') {
 const iso = activityInstant(value);
 if (!iso) return /^\d{4}-\d{2}-\d{2}$/.test(text(value, '')) ? dateText(value) : 'Not provided';
 try {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone, day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23', timeZoneName: 'short' }).formatToParts(new Date(iso));
  const part = (name: string) => parts.find(p => p.type === name)?.value ?? '';
  const zone = ['Asia/Calcutta', 'Asia/Kolkata'].includes(timeZone) ? 'IST' : timeZone === 'UTC' ? 'UTC' : part('timeZoneName');
  return `${part('day')} ${part('month')} ${part('year')}, ${part('hour')}:${part('minute')}:${part('second')} ${zone}`;
 } catch { return activityTimeText(value, 'UTC'); }
}
