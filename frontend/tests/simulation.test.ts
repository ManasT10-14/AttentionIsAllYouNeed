import test from 'node:test';
import assert from 'node:assert/strict';
import { demoPortfolio } from '../src/lib/demo-data';
import { portfolioSchema } from '../src/lib/models';
import { addDays, daysBetween, monthEnds, projectObligation, projectPortfolio, projectionSeries } from '../src/lib/simulation';

test('no urgent obligation is represented as numeric zero at the initial date', () => {
  const result = projectPortfolio(demoPortfolio, demoPortfolio.asOf);
  assert.equal(result.urgent.length, 0);
  assert.equal(String(result.urgent.length), '0');
  assert.equal(result.triggered, 0);
});
test('a deadline day is due today without a premature fixed charge', () => {
  const renewal = demoPortfolio.obligations.find(item => item.id === 'renewal')!;
  assert.equal(projectObligation(renewal, '2026-11-19').status, 'Due today');
  assert.equal(projectObligation(renewal, '2026-11-19').triggered, 0);
  assert.equal(projectObligation(renewal, '2026-11-20').triggered, 24000);
});
test('daily charges include the first overdue day and accrue consistently', () => {
  const payment = demoPortfolio.obligations.find(item => item.id === 'payment')!;
  assert.equal(projectObligation(payment, '2026-12-01').triggered, 0);
  assert.equal(projectObligation(payment, '2026-12-02').triggered, 18750);
  assert.equal(projectObligation(payment, '2026-12-31').triggered, 26000);
});
test('the seven-day warning boundary is inclusive', () => {
  const renewal = demoPortfolio.obligations.find(item => item.id === 'renewal')!;
  assert.equal(projectObligation(renewal, '2026-11-11').status, 'Upcoming');
  assert.equal(projectObligation(renewal, '2026-11-12').status, 'At risk');
});
test('moving the clock backward removes costs and does not mutate the contract', () => {
  const before = structuredClone(demoPortfolio);
  assert.equal(projectPortfolio(demoPortfolio, '2026-12-31').triggered, 71700);
  assert.equal(projectPortfolio(demoPortfolio, '2026-10-25').triggered, 0);
  assert.deepEqual(demoPortfolio, before);
});
test('month-end heatmap and timeline return identical results for the same date', () => {
  for (const month of monthEnds(demoPortfolio.asOf)) {
    const individual = demoPortfolio.obligations.reduce((sum, item) => sum + projectObligation(item, month.date).triggered, 0);
    assert.equal(projectPortfolio(demoPortfolio, month.date).triggered, individual);
  }
});
test('date arithmetic is deterministic across year and leap-day boundaries', () => {
  assert.equal(addDays('2026-12-31', 1), '2027-01-01');
  assert.equal(addDays('2028-02-28', 1), '2028-02-29');
  assert.equal(daysBetween('2026-10-25', '2027-01-23'), 90);
  assert.deepEqual(monthEnds('2026-12-25').map(item => item.date), ['2026-12-31', '2027-01-31', '2027-02-28', '2027-03-31']);
});
test('the chart samples the same model and ends at day 90', () => {
  const series = projectionSeries(demoPortfolio);
  assert.equal(series.length, 91);
  assert.equal(series[90].date, '2027-01-23');
  assert.equal(series[90].triggered, projectPortfolio(demoPortfolio, series[90].date).triggered);
});
test('integration payloads reject missing evidence and dangling references', () => {
  const missing = structuredClone(demoPortfolio);
  missing.obligations[0].contractId = 'unknown';
  assert.equal(portfolioSchema.safeParse(missing).success, false);
  const dangling = structuredClone(demoPortfolio);
  dangling.actions[0].obligationId = 'unknown';
  assert.equal(portfolioSchema.safeParse(dangling).success, false);
});
