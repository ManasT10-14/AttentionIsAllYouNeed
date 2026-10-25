"""Report dict → HTML (UI + PDF export via pymupdf Story)."""
from __future__ import annotations

import html
import io

import fitz

E = html.escape


def _money(x, ccy="INR"):
    return f"{ccy} {x:,.0f}" if isinstance(x, (int, float)) else "—"


def _cites(cs) -> str:
    return ", ".join(f"<a href='{E(c.get('link') or '')}'>{E(c['contract_id'])} §{E(c['clause_number'])}</a>"
                     f"{'' if c.get('verified') else ' (unverified)'}" for c in (cs or []))


def contract_html(r: dict) -> str:
    s = r.get("summary") or {}
    exp = r.get("exposure") or {}
    rows = "".join(f"<tr><td>{E(str(e['date']))}</td><td>{E(e['kind'])}</td><td>{E(e['title'])}</td>"
                   f"<td>{E(e['status'])}</td><td>{_money(e['amount']['amount'], e['amount']['currency']) if e.get('amount') else ''}</td></tr>"
                   for e in r.get("timeline", [])[:40])
    risks = "".join(f"<li><b>[{f.get('severity')}/5 · p={f.get('likelihood')}] {E(f.get('kind', ''))}</b> — {E(f.get('claim', ''))}"
                    f" <i>({E(f.get('status', ''))})</i><br><small>{_cites(f.get('citations'))}</small></li>"
                    for f in r.get("risks", [])[:25])
    acts = "".join(f"<li><b>{E(a['kind'])}</b>: {E(a['subject'])} (deadline {E(str(a.get('deadline')))}, conf "
                   f"{a.get('confidence')}, {'needs approval' if a.get('needs_human_approval') else 'auto'})"
                   f"<br><small>{_cites(a.get('citations'))}</small></li>" for a in r.get("actions", [])[:15])
    refs = "".join(f"<li>{E(c['contract_id'])} §{E(c['clause_number'])} p.{c.get('page') or '?'}: "
                   f"“{E((c.get('quote') or '')[:240])}”</li>" for c in r.get("references", [])[:60])
    return f"""<h1>{E(r.get('title') or r['contract_id'])} <small>v{r.get('version')}</small></h1>
<p><b>Completeness:</b> {E(str(r.get('completeness')))} {E(r.get('gaps') or '')} · <b>As of</b> {E(r.get('as_of', ''))}
· <b>Health</b> {r.get('health', {}).get('score')}</p>
<h2>Executive summary <small>(ANALYSIS)</small></h2><p>{E(s.get('executive_summary', ''))}</p>
<h2>Exposure <small>(ANALYSIS)</small></h2><p>Expected {_money(exp.get('expected'), exp.get('currency', 'INR'))} ·
Worst case {_money(exp.get('worst_case'), exp.get('currency', 'INR'))}</p>
<h2>Timeline</h2><table border=1 cellpadding=3><tr><th>Date</th><th>Kind</th><th>Item</th><th>Status</th><th>Amount</th></tr>{rows}</table>
<h2>Risks (Loki → Heimdall → Tyr)</h2><ul>{risks}</ul>
<h2>Recommended actions</h2><ul>{acts}</ul>
<h2>References <small>(SOURCED clause text)</small></h2><ol>{refs}</ol>"""


def company_html(r: dict) -> str:
    s = r.get("summary") or {}
    exp = r.get("total_exposure") or {}
    confl = "".join(f"<li>[{f.get('severity')}/5] {E(f.get('claim', ''))}<br><small>{_cites(f.get('citations'))}</small></li>"
                    for f in r.get("conflicts", []))
    acts = "".join(f"<li><b>{E(a['contract_id'])}</b> · {E(a['kind'])}: {E(a['subject'])} (priority {a.get('priority')}, "
                   f"deadline {E(str(a.get('deadline')))})</li>" for a in r.get("prioritized_actions", []))
    worst = "".join(f"<tr><td>{E(str(e['date']))}</td><td>{E(e['contract_id'])}</td><td>{E(e['title'])}</td>"
                    f"<td>{E(e['status'])}</td><td>{_money(e['amount']['amount'], e['amount']['currency'])}</td></tr>"
                    for e in r.get("worst_case_projection", [])[:40])
    refs = "".join(f"<li>{E(c['contract_id'])} §{E(c['clause_number'])}: “{E((c.get('quote') or '')[:200])}”</li>"
                   for c in r.get("references", [])[:80])
    ws = ", ".join(f"{E(k)}: {E(str(v))}" for k, v in (r.get("workstreams") or {}).items())
    return f"""<h1>Company Risk Report</h1><p><b>Completeness:</b> {E(r.get('completeness', ''))} ({ws}) · <b>As of</b> {E(r.get('as_of', ''))}</p>
<h2>Executive summary <small>(ANALYSIS)</small></h2><p>{E(s.get('executive_summary', ''))}</p>
<ul>{''.join(f'<li>{E(k)}</li>' for k in s.get('key_risks', []))}</ul>
<h2>Total financial exposure</h2><p>Expected {_money(exp.get('expected'), exp.get('currency', 'INR'))} · Worst case
{_money(exp.get('worst_case'), exp.get('currency', 'INR'))} <small>{E(exp.get('note', ''))}</small></p>
<h2>Cross-contract conflicts</h2><ul>{confl or '<li>None found</li>'}</ul>
<h2>Prioritized actions</h2><ol>{acts}</ol>
<h2>Worst-case projection (no action taken)</h2><table border=1 cellpadding=3><tr><th>Date</th><th>Contract</th><th>Item</th><th>Status</th><th>Amount</th></tr>{worst}</table>
<h2>References</h2><ol>{refs}</ol>"""


def _li(items, fmt) -> str:
    return "".join(f"<li>{fmt(x)}</li>" for x in items) or "<li>None</li>"


def _ruling(f: dict, rul: dict) -> str:
    r = rul.get(f["id"])
    tail = f"{E(r['winner'])}, severity {r['final_severity']}/5 - {E(r['rationale'])}" if r else "pending"
    return f"{E(f['claim'])}<br><small>Ruling: {tail}</small>"


def event_html(r: dict) -> str:
    ev = r.get("event") or {}
    ex = r.get("exposure_delta")
    rul = {x.get("finding_id"): x for x in r.get("rulings", [])}
    return f"""<h1>Event report: {E(ev.get('subject') or ev.get('event_type', ''))}</h1>
<p><b>Type</b> {E(str(ev.get('event_type')))} · <b>Occurred</b> {E(str(ev.get('occurred_at')))} · <b>Status</b> {E(str(ev.get('status')))}
 · <b>Runs</b> {E(', '.join(r.get('run_ids', [])) or 'n/a')}</p>
<h2>Affected contracts</h2><p>{E(', '.join(r.get('affected_contracts', [])) or 'None')}</p>
<h2>Exposure delta <small>(ANALYSIS)</small></h2><p>{_money(ex['amount'], ex['currency']) if ex else 'No quantified exposure'}</p>
<h2>New violations</h2><ul>{_li(r.get('violations', []), lambda v: f"<b>{E(v['contract_id'])} §{E(v['clause_number'])}</b> {E(v['breach_type'])} ({E(v['status'])}): {E(v.get('explanation', ''))}")}</ul>
<h2>Alerts</h2><ul>{_li(r.get('alerts', []), lambda a: f"[{E(a['severity'])}] {E(a['title'])} - {E(a.get('why', ''))}")}</ul>
<h2>Actions</h2><ul>{_li(r.get('actions', []), lambda a: f"<b>{E(a['kind'])}</b>: {E(a['subject'])} ({E(a['status'])})")}</ul>
<h2>Tyr rulings</h2><ul>{_li(r.get('findings', []), lambda f: _ruling(f, rul))}</ul>
<h2>Affected clauses</h2><ol>{_li(r.get('affected_clauses', []), lambda c: f"{E(c['contract_id'])} §{E(c['clause_number'])}: {E((c.get('quote') or '')[:240])}")}</ol>"""


def _chg(x: dict) -> str:
    return f"{E(str(x.get('contract_id')))}: {E(x.get('claim') or x.get('subject') or '')}"


def run_html(r: dict) -> str:
    d = r.get("diff") or {}
    ex = d.get("exposure_delta")
    since = f"the previous run {E((r.get('previous_run_id') or '')[:8])}" if r.get("previous_run_id") else "nothing (first run)"
    delta = (f"expected {_money(ex['expected'], ex['currency'])}, worst case {_money(ex['worst_case'], ex['currency'])}"
             if ex else "n/a")
    head = (f"<h1>Workflow report - run {E(r['run_id'][:8])} <small>({E(r['run_kind'])}, {E(r['generated_at'][:19])})</small></h1>"
            f"<h2>What changed since {since}</h2><p>Exposure change: {delta}</p>"
            f"<h3>New findings</h3><ul>{_li(d.get('new_findings', []), _chg)}</ul>"
            f"<h3>Resolved findings</h3><ul>{_li(d.get('resolved_findings', []), _chg)}</ul>"
            f"<h3>New actions</h3><ul>{_li(d.get('new_actions', []), _chg)}</ul>"
            f"<h3>Resolved actions</h3><ul>{_li(d.get('resolved_actions', []), _chg)}</ul>")
    return head + company_html(r.get("report") or {})


def to_pdf(body_html: str) -> bytes:
    story = fitz.Story(html=f"<body style='font-family:sans-serif;font-size:9pt'>{body_html}</body>")
    buf = io.BytesIO()
    writer = fitz.DocumentWriter(buf)
    rect = fitz.paper_rect("a4")
    more = 1
    while more:
        dev = writer.begin_page(rect)
        more, _ = story.place(rect + (40, 40, -40, -40))
        story.draw(dev)
        writer.end_page()
    writer.close()
    return buf.getvalue()
