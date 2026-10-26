"""ToolRegistry — the single choke point for every agent capability (plan R5).

Each tool declares scope / side_effect / requires_approval / pii. Every invocation:
  allowlist check → HOOKS.pre_tool (security suite) → approval gate → run → HOOKS.post_tool
  → audit row in `tool_calls` → LangSmith-visible via the surrounding traced node.
LLM-visible tools are bound to models through `langchain_tools()`; node code calls `invoke()` directly,
so writes take exactly the same audited path as LLM-chosen reads.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal, Type

from langchain_core.tools import StructuredTool
from odin.core.context import maybe_current
from odin.core.hooks import HOOKS, Blocked
from odin.core.models import new_id
from odin.core.privacy import redact, redact_text
from odin.db.session import db
from odin.db.tables import ToolCall
from odin.services.approvals import ApprovalRequired
from pydantic import BaseModel

Scope = Literal["read_contract", "read_state", "write_state", "retrieval", "external_send", "file_write"]


class ToolDenied(Exception):
    pass


@dataclass
class ToolSpec:
    name: str
    fn: Callable[..., Any]
    args: Type[BaseModel]
    description: str
    scope: Scope
    side_effect: bool = False
    requires_approval: bool = False
    pii: bool = False
    llm_visible: bool = True


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, ToolSpec] = {}
        self.allow: dict[str, set[str]] = {}

    # ── registration ──
    def tool(self, *, args: Type[BaseModel], scope: Scope, side_effect=False, requires_approval=False, pii=False,
             llm_visible=True):
        def deco(fn):
            self.tools[fn.__name__] = ToolSpec(fn.__name__, fn, args, (fn.__doc__ or "").strip(), scope,
                                               side_effect, requires_approval, pii, llm_visible)
            return fn
        return deco

    def grant(self, agent: str, *names: str) -> None:
        missing = [n for n in names if n not in self.tools]
        if missing:
            raise KeyError(f"unknown tools {missing}")
        self.allow.setdefault(agent, set()).update(names)

    # ── execution ──
    def invoke(self, agent: str, name: str, args: dict | BaseModel | None = None, *, approval_id: str | None = None):
        from odin.core.telemetry import _plain, _set_outputs, span
        ins = args.model_dump(mode="json") if isinstance(args, BaseModel) else dict(args or {})
        with span(f"tool:{name}", "tool", inputs={"agent": agent, "args": _plain(ins)}, metadata={"agent": agent},
                  tags=[agent]) as run:
            out = self._invoke(agent, name, args, approval_id=approval_id)
            _set_outputs(run, out)
            return out

    def _invoke(self, agent, name, args=None, *, approval_id=None):
        payload = args.model_dump(mode="json") if isinstance(args, BaseModel) else dict(args or {})
        spec = self.tools.get(name)
        t0 = time.perf_counter()
        decision = {"tool": name, "authorized": False, "approved": None,
                    "executed": False, "ok": False}
        try:
            if not spec:
                raise ToolDenied(f"unknown tool {name}")
            if name not in self.allow.get(agent, set()):
                raise ToolDenied(f"agent '{agent}' may not call '{name}'")
            decision["authorized"] = True
            # Missing approval is a deterministic denial even without a tenant context;
            # payload validation and the atomic claim still occur after guards below.
            if spec.requires_approval and not approval_id:
                decision["approved"] = False
                raise ApprovalRequired("this tool needs a payload-bound admin approval")
            c = maybe_current()
            if c and c.run_id:
                from odin.core.budget import for_run
                for_run(c.run_id).tool_calls += 1
            payload = HOOKS.pre_tool(agent, name, spec.scope, payload)
            parsed = spec.args.model_validate(payload)
            # Hash exactly the validated/defaulted values passed to the effect, after guards.
            payload = parsed.model_dump(mode="json")
            execution_id = None
            if spec.requires_approval:
                decision["approved"] = False
                execution_id = self._check_approval(approval_id, name, payload)
                decision["approved"] = True
            try:
                if execution_id:
                    from odin.services.approvals import dispatch_context, revalidate_claim
                    revalidate_claim(approval_id, execution_id, name, payload)
                    with dispatch_context(approval_id, execution_id, name, payload):
                        decision["executed"] = True
                        result = spec.fn(parsed)
                else:
                    decision["executed"] = True
                    result = spec.fn(parsed)
            except Exception:
                if execution_id:
                    from odin.services.approvals import finish
                    finish(approval_id, execution_id, ok=False, tool=name, dispatched=decision["executed"])
                raise
            if execution_id:
                from odin.services.approvals import finish
                finish(approval_id, execution_id, ok=True, tool=name)
            result = HOOKS.post_tool(agent, name, result)
            decision["ok"] = True
            self._audit(agent, spec, payload, self.render(redact(result), 300), ok=True, t0=t0)
            return result
        except Exception as e:
            decision["error_type"] = type(e).__name__
            if spec:
                self._audit(agent, spec, payload, redact_text(f"{type(e).__name__}: {e}")[:500], ok=False,
                            blocked=isinstance(e, (Blocked, ToolDenied, ApprovalRequired)), t0=t0)
            raise
        finally:
            HOOKS.record("tool", agent, redact(payload), None, redact(decision))

    def _check_approval(self, approval_id: str | None, tool: str | None = None, payload: dict | None = None) -> str:
        from odin.services.approvals import claim
        if not tool or payload is None:
            raise ApprovalRequired("approval requires an exact tool and payload")
        return claim(approval_id, tool, payload)

    def _audit(self, agent, spec: ToolSpec, args, summary, ok=True, blocked=False, t0=None):
        c = maybe_current()
        if not c:
            return
        safe_args = redact({k: ("<redacted>" if spec.pii and k in ("body", "to") else v)
                            for k, v in (args or {}).items()})
        try:
            with db() as s:
                s.add(ToolCall(id=new_id("tc"), company_id=c.company_id, run_id=c.run_id, agent=agent, tool=spec.name,
                               scope=spec.scope, args=json.loads(json.dumps(safe_args, default=str))
                               if len(json.dumps(safe_args, default=str)) < 20000 else {"truncated": True},
                               result_summary=redact_text(summary), ok=ok, blocked=blocked,
                               duration_ms=(time.perf_counter() - t0) * 1000 if t0 else 0))
        except Exception:   # audit must not take the product path down
            pass

    # ── LLM binding ──
    def langchain_tools(self, agent: str, names: list[str]) -> list[StructuredTool]:
        out = []
        for n in names:
            spec = self.tools.get(n)
            if not spec or not spec.llm_visible or spec.side_effect or n not in self.allow.get(agent, set()):
                continue
            out.append(StructuredTool.from_function(func=lambda **kw: None, name=n, description=spec.description,
                                                    args_schema=spec.args))
        return out

    @staticmethod
    def render(result: Any, limit: int = 6000) -> str:
        if isinstance(result, BaseModel):
            result = result.model_dump(mode="json")
        s = json.dumps(result, default=str, ensure_ascii=False)
        return s if len(s) <= limit else s[:limit] + "…(truncated)"

    def describe(self) -> list[dict]:
        return [{"name": s.name, "scope": s.scope, "side_effect": s.side_effect,
                 "requires_approval": s.requires_approval, "pii": s.pii, "llm_visible": s.llm_visible,
                 "allowed_agents": sorted(a for a, ns in self.allow.items() if s.name in ns),
                 "description": s.description, "args_schema": s.args.model_json_schema()}
                for s in self.tools.values()]


REGISTRY = ToolRegistry()
