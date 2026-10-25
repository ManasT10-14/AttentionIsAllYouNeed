import type { Obligation, Portfolio } from './models';

export const DAY_MS = 86400000;
export const currency = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
export const shortCurrency = (value: number) => value >= 1000 ? `$${(value / 1000).toFixed(value % 1000 ? 1 : 0)}k` : currency(value);
export const dateLabel = (date: string, long = false) => new Date(`${date}T00:00:00Z`).toLocaleDateString('en-US', { month: long ? 'long' : 'short', day: 'numeric', year: long ? 'numeric' : undefined, timeZone: 'UTC' });
export const daysBetween = (start: string, end: string) => Math.round((Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) / DAY_MS);
export const addDays = (date: string, days: number) => new Date(Date.parse(`${date}T00:00:00Z`) + days * DAY_MS).toISOString().slice(0, 10);

export function projectObligation(obligation: Obligation, date: string) {
  const remaining = daysBetween(date, obligation.deadline);
  const overdueDays = Math.max(0, -remaining);
  const triggered = remaining < 0 ? obligation.amount + overdueDays * obligation.dailyPenalty : 0;
  const status = remaining < 0 ? 'Overdue' : remaining === 0 ? 'Due today' : remaining <= 7 ? 'At risk' : 'Upcoming';
  return { ...obligation, remaining, overdueDays, triggered, potential: obligation.amount + overdueDays * obligation.dailyPenalty, status };
}
export type ProjectedObligation = ReturnType<typeof projectObligation>;
export function projectPortfolio(portfolio: Portfolio, date: string) {
  const obligations = portfolio.obligations.map(item => projectObligation(item, date));
  return {
    obligations,
    triggered: obligations.reduce((sum, item) => sum + item.triggered, 0),
    potential: obligations.reduce((sum, item) => sum + item.potential, 0),
    urgent: obligations.filter(item => item.remaining <= 7),
    upcoming: obligations.filter(item => item.remaining >= 0 && item.remaining <= 30),
    overdue: obligations.filter(item => item.remaining < 0)
  };
}
export function projectionSeries(portfolio: Portfolio) {
  return Array.from({ length: 91 }, (_, day) => {
    const date = addDays(portfolio.asOf, day);
    const result = projectPortfolio(portfolio, date);
    return { date, day, label: dateLabel(date), triggered: result.triggered, potential: result.potential };
  });
}
export function monthEnds(start: string) {
  const date = new Date(`${start}T00:00:00Z`);
  return Array.from({ length: 4 }, (_, offset) => {
    const end = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + offset + 1, 0));
    return { date: end.toISOString().slice(0, 10), label: end.toLocaleDateString('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' }) };
  });
}
