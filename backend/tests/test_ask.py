"""Ask Odin portfolio path with the fake provider: no DB, no network."""
from types import SimpleNamespace as NS

from odin.services import ask as ask_mod


def test_classify():
    assert ask_mod.classify("what contracts do we have?") == "portfolio"
    assert ask_mod.classify("Which contracts renew next quarter") == "portfolio"
    assert ask_mod.classify("Is the supplier liable for late delivery?") == "clause"


def test_portfolio_question_answers_without_clause_evidence(monkeypatch):
    seen = {}
    c = NS(contract_id="CLOUD-1", title="Cloud Services Agreement", type="saas", status="active",
           meta={"parties": [{"name": "Acme", "role": "company"}, {"name": "AWS", "role": "vendor"}]})
    monkeypatch.setattr(ask_mod.repo, "contracts", lambda: [c])
    monkeypatch.setattr(ask_mod.repo, "sim_now", lambda: __import__("datetime").date(2026, 1, 1))
    monkeypatch.setattr(ask_mod.insights, "exposure_summary", lambda now=None: {
        "expected": 10.0, "worst_case": 20.0, "currency": "INR", "note": "n",
        "contracts": [{"contract_id": "CLOUD-1", "expected": 10.0, "worst_case": 20.0, "term_end": "2026-12-31",
                       "notice_deadline": "2026-10-01"}]})
    monkeypatch.setattr(ask_mod.insights, "extraction", lambda cid: None)
    monkeypatch.setattr(ask_mod.insights, "counterparties", lambda now=None: [])
    monkeypatch.setattr(ask_mod.insights, "alerts", lambda now=None: [])
    monkeypatch.setattr(ask_mod.hybrid, "search", lambda *a, **k: [])
    monkeypatch.setattr(ask_mod, "run_ctx", lambda *a, **k: __import__("contextlib").nullcontext())
    monkeypatch.setattr("odin.llm.call.chain_for", lambda agent: ["fake"])
    real = ask_mod.structured
    monkeypatch.setattr(ask_mod, "structured",
                        lambda agent, schema, system, user, **k: seen.setdefault("user", user) and real(
                            agent, schema, system, user))
    monkeypatch.setattr(ask_mod, "traced", lambda *a, **k: (lambda f: f), raising=False)
    out = ask_mod.ask("co", "summarise the cloud agreement")
    assert out["kind"] == "portfolio" and not out["passages"]
    assert out["sources"] == [{"contract_id": "CLOUD-1", "title": "Cloud Services Agreement"}]
    assert "CLOUD-1" in seen["user"] and "AWS" in seen["user"]
    assert out["answer"]   # fake provider answered instead of refusing for lack of clauses
