"""Per-run budget: agent calls, tokens, USD (FR7.2, NFR5). Shared by parallel workstreams."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field, fields

from odin.core.config import limits


class BudgetExceeded(Exception):
    pass


@dataclass
class Budget:
    run_id: str
    max_agent_calls: int
    max_tokens: int
    max_usd: float
    agent_calls: int = 0
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    usd: float = 0.0
    fallbacks: int = 0
    per_agent: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def exhausted(self) -> str | None:
        if self.agent_calls >= self.max_agent_calls:
            return f"agent call budget reached ({self.agent_calls}/{self.max_agent_calls})"
        if self.tokens_in + self.tokens_out >= self.max_tokens:
            return f"token budget reached ({self.tokens_in + self.tokens_out}/{self.max_tokens})"
        if self.usd >= self.max_usd:
            return f"USD budget reached (${self.usd:.3f}/${self.max_usd})"
        return None

    def check(self) -> None:
        reason = self.exhausted()
        if reason:
            raise BudgetExceeded(reason)

    def charge(self, agent: str, tokens_in: int = 0, tokens_out: int = 0, usd: float = 0.0,
               provider: str = "", latency_ms: float = 0.0, fallback: bool = False) -> None:
        with self._lock:
            self.agent_calls += 1
            self.tokens_in += tokens_in
            self.tokens_out += tokens_out
            self.usd += usd
            self.fallbacks += int(fallback)
            a = self.per_agent.setdefault(agent, {"calls": 0, "tokens": 0, "usd": 0.0, "latency_ms": 0.0,
                                                  "providers": {}})
            a["calls"] += 1
            a["tokens"] += tokens_in + tokens_out
            a["usd"] = round(a["usd"] + usd, 6)
            a["latency_ms"] += latency_ms
            a["providers"][provider] = a["providers"].get(provider, 0) + 1

    def to_dict(self) -> dict:
        with self._lock:
            d = {f.name: getattr(self, f.name) for f in fields(self) if f.name != "_lock"}
            d["per_agent"] = {k: {**v, "providers": dict(v["providers"])} for k, v in self.per_agent.items()}
        d["usd"] = round(self.usd, 5)
        return d


_budgets: dict[str, Budget] = {}
_glock = threading.Lock()


def for_run(run_id: str | None) -> Budget:
    """Budget of a run; a throwaway unlimited-ish one when called outside a run."""
    key = run_id or "__adhoc__"
    with _glock:
        if key not in _budgets:
            lim = limits()
            _budgets[key] = Budget(run_id=key, max_agent_calls=lim["max_agent_calls"],
                                   max_tokens=lim["max_tokens"], max_usd=lim["max_usd"])
        return _budgets[key]


def override(run_id: str, **lims) -> Budget:
    b = for_run(run_id)
    for k, v in lims.items():
        setattr(b, k, v)
    return b


def release(run_id: str) -> dict:
    with _glock:
        b = _budgets.pop(run_id, None)
    return b.to_dict() if b else {}
