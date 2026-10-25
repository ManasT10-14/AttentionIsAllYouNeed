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
from pydantic import BaseModel

from odin.core.context import maybe_current
from odin.core.hooks import HOOKS, Blocked
from odin.core.models import new_id
from odin.db.session import db
from odin.db.tables import ToolCall

Scope = Literal["read_contract", "read_state", "write_state", "retrieval", "external_send", "file_write"]


class ToolDenied(Exception):
    pass


class ApprovalRequired(Exception):
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
        spec = self.tools.get(name)
        if not spec:
            raise ToolDenied(f"unknown tool {name}")
        if name not in self.allow.get(agent, set()):
            self._audit(agent, spec, {}, f"denied: {agent} not allowed", ok=False, blocked=True)
            raise ToolDenied(f"agent '{agent}' may not call '{name}'")
        payload = args.model_dump(mode="json") if isinstance(args, BaseModel) else dict(args or {})
        c = maybe_current()
        if c and c.run_id:
            from odin.core.budget import for_run
            for_run(c.run_id).tool_calls += 1
        t0 = time.perf_counter()
        try:
            payload = HOOKS.pre_tool(agent, name, spec.scope, payload)
            if spec.requires_approval:
                self._check_approval(approval_id)
            parsed = spec.args.model_validate(payload)
            result = spec.fn(parsed)
            result = HOOKS.post_tool(agent, name, result)
        except Blocked as e:
            self._audit(agent, spec, payload, f"blocked by guard: {e}", ok=False, blocked=True, t0=t0)
            raise
        except Exception as e:
            self._audit(agent, spec, payload, f"{type(e).__name__}: {e}"[:500], ok=False, t0=t0)
            raise
        self._audit(agent, spec, payload, self.render(result, 300), ok=True, t0=t0)
        return result

    def _check_approval(self, approval_id: str | None) -> None:
        from odin.db import repo
        if not approval_id:
            raise ApprovalRequired("this tool needs an approved action (approval_id)")
        a = repo.get("action", approval_id)
        if not a or a.get("status") not in ("approved",):
            raise ApprovalRequired(f"action {approval_id} is not approved by an admin")

    def _audit(self, agent, spec: ToolSpec, args, summary, ok=True, blocked=False, t0=None):
        c = maybe_current()
        if not c:
            return
        safe_args = {k: ("<redacted>" if spec.pii and k in ("body", "to") else v) for k, v in (args or {}).items()}
        try:
            with db() as s:
                s.add(ToolCall(id=new_id("tc"), company_id=c.company_id, run_id=c.run_id, agent=agent, tool=spec.name,
                               scope=spec.scope, args=json.loads(json.dumps(safe_args, default=str))
                               if len(json.dumps(safe_args, default=str)) < 20000 else {"truncated": True},
                               result_summary=summary, ok=ok, blocked=blocked,
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
