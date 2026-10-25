"""Latency work: severity-gated debate, one batched Heimdall call, per-contract early start."""
import threading
import time
from types import SimpleNamespace

from odin.agents import heimdall
from odin.core.models import HeimdallVerifications, VerificationDraft
from odin.graphs import analysis


def test_heimdall_one_batched_call_and_severity_gate(monkeypatch):
    findings = {f"f{s}": {"id": f"f{s}", "severity": s, "status": "open", "citations": []} for s in (1, 2, 3, 5)}
    calls = []

    def fake_structured(agent, schema, system, user, **kw):
        calls.append(agent)
        return HeimdallVerifications(verifications=[
            VerificationDraft(finding_id=i, verdict="challenge", rationale="x") for i in findings])

    monkeypatch.setattr(heimdall, "structured", fake_structured)
    monkeypatch.setattr(heimdall, "say", lambda *a, **k: None)
    monkeypatch.setattr(heimdall, "tool", lambda name, args: [] if name == "get_events" else None)
    monkeypatch.setattr(heimdall.repo, "query", lambda *a, **k: list(findings.values()))
    monkeypatch.setattr(heimdall.repo, "get", lambda kind, i: findings[i])
    monkeypatch.setattr(heimdall.repo, "set_status", lambda *a, **k: None)
    out = heimdall.verify.__wrapped__({"contract_id": "c1"})
    assert len(calls) == 1                               # all four findings verified in ONE call
    assert out["disputed"] == ["f3", "f5"]               # severity < 3 never enters the debate


def test_pipeline_starts_loki_per_contract_and_cross_waits(monkeypatch):
    log, lock = [], threading.Lock()
    mark = lambda s: (lock.acquire(), log.append(s), lock.release())

    def ext(p):
        time.sleep(0.4 if p["contract_id"] == "slow" else 0.0)
        mark(f"extracted:{p['contract_id']}")
        return {"errors": []}

    class WS:
        def invoke(self, p):
            mark(f"ws:{p['contract_id']}")
            return {"ws_results": [{"contract_id": p["contract_id"], "status": "done"}]}

    monkeypatch.setattr(analysis, "extract", ext)
    monkeypatch.setattr(analysis.contract_ws, "build", lambda: WS())
    monkeypatch.setattr(analysis.synth, "synthesize_contract", lambda s: mark(f"report:{s['contract_id']}"))
    analysis._extracted["r"] = {c: threading.Event() for c in ("fast", "slow")}
    ts = [threading.Thread(target=lambda c=c: analysis.pipeline({"run_id": "r", "contract_id": c}))
          for c in ("slow", "fast")]
    ts.append(threading.Thread(target=lambda: analysis.cross({"run_id": "r", "contract_id": "cross"})))
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert log.index("report:fast") < log.index("extracted:slow")      # fast contract fully reported first
    assert log.index("ws:cross") > log.index("extracted:slow")         # cross waits for all extractions
