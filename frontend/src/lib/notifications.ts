import { dateText, daysBetween, isIsoDate, query, text, type ApiRecord } from './api';

export type Notice = { id: number; title: string; href: string; detail?: string; category?: 'deadline'; toast?: boolean; key?: string; asOf?: string };
export function isDeadlineAlert(alert: ApiRecord) {
 return isIsoDate(alert.due_date) && !['event', 'cascade'].includes(text(alert.kind, ''));
}
/** Only active deadlines within seven days of the committed workspace date qualify. */
export function upcomingDeadlineNotices(alerts: ApiRecord[], asOf: string, seen: ReadonlySet<string>, now: number, preview = false): Notice[] {
 if (!isIsoDate(asOf)) return [];
 const notices: Notice[] = []; const keys = new Set(seen);
 for (const alert of alerts) {
  if (!isDeadlineAlert(alert) || !['open', 'pending'].includes(text(alert.status, 'open'))) continue;
  const due = text(alert.due_date); const days = daysBetween(asOf, due);
  if (days < 0 || days > 7) continue;
  const bucket = days === 0 ? 'today' : days === 1 ? 'tomorrow' : days <= 3 ? '3-days' : '7-days';
  const identity = text(alert.dedupe_key ?? alert.id, [alert.contract_id, due, alert.title].join('|'));
  const key = `${identity}|${due}|${bucket}`;
  if (keys.has(key)) continue;
  keys.add(key);
  const when = days === 0 ? 'Due today' : days === 1 ? 'Due tomorrow' : `Due in ${days} days`;
  notices.push({ id: now + notices.length, category: 'deadline', toast: true, key, asOf,
   title: `${preview ? 'Sample · ' : ''}${when}: ${text(alert.title, 'Contract deadline')}`,
   detail: `${dateText(due)}${alert.contract_id ? ' · ' + text(alert.contract_id) : ''}. ${text(alert.why, '')} Based on workspace date ${dateText(asOf)}.`,
   href: query('/dashboard/timeline', { contract_id: text(alert.contract_id, '') || undefined, month: due.slice(0, 7) }),
  });
 }
 return notices;
}
