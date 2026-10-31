"""The one door every agent uses to talk to an LLM.

  structured(agent, Schema, system, user, tools=[...])  →  Schema instance

Handles: guard hooks, budget checks/charging, provider fallback chain with retries, an optional
bounded tool-calling phase (tools executed through the ToolRegistry → audited + guarded),
structured output via function calling, schema-repair retry, LangSmith run names/tags/metadata,
and eval hook recording.
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Type, TypeVar

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from odin.core import budget as budget_mod
from odin.core.config import limits, odin_config
from odin.core.context import maybe_current
from odin.core.hooks import HOOKS, Blocked
from odin.core.privacy import redact, redact_text
from odin.core.telemetry import traced
from odin.llm.factory import chain_for, chat_model, max_tokens_for, model_for, price
from odin.llm.fake import fake_instance
from pydantic import BaseModel

log = logging.getLogger("odin.llm")
T = TypeVar("T", bound=BaseModel)


class LLMFailure(Exception):
    pass


def _usage(msg) -> tuple[int, int]:
    u = getattr(msg, "usage_metadata", None) or {}
    return int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0))


def _run_config(agent: str, provider: str, prompt_hash: str, extra: dict | None) -> dict:
    c = maybe_current()
    meta = {"agent": agent, "provider": provider, "prompt_hash": prompt_hash, **(extra or {})}
    tags = [agent, provider]
    if (extra or {}).get("contract_id"):
        tags.append(f"contract:{extra['contract_id']}")
    if c:
        meta.update(company_id=c.company_id, run_id=c.run_id, scenario_id=c.scenario_id)
        if c.scenario_id:
            tags.append("whatif")
    meta["run_kind"] = (extra or {}).get("run_kind") or (c.agent if c else None)
    return redact({"run_name": f"{agent}:{provider}", "tags": tags, "metadata": {k: v for k, v in meta.items() if v is not None}})


@traced("odin:structured")
def structured(agent: str, schema: Type[T], system: str, user: str, *, tools: list[str] | None = None,
               meta: dict | None = None) -> T:
    c = maybe_current()
    bud = budget_mod.for_run(c.run_id if c else None)
    bud.check()
    messages = [SystemMessage(system), HumanMessage(user)]
    messages = HOOKS.pre_llm(agent, messages)
    prompt_hash = hashlib.sha1(system.encode()).hexdigest()[:10]
    agent_options = odin_config()["agents"].get(agent) or {}
    retries = agent_options.get("max_retries", odin_config()["defaults"].get("max_retries", 2))
    providers = chain_for(agent)
    errors = []

    for i, prov in enumerate(providers):
        if prov == "fake":
            out = fake_instance(schema)
            bud.charge(agent, provider="fake", fallback=i > 0)
            return _finish(agent, schema, messages, out, prov, meta)
        for attempt in range(retries + 1):
            t0 = time.perf_counter()
            try:
                cfg = _run_config(agent, prov, prompt_hash, meta)
                model = chat_model(prov, odin_config()["defaults"].get("temperature", 0), model_for(agent, prov),
                                   max_tokens_for(agent), timeout_s=agent_options.get("timeout_s", 120))
                convo = list(messages)
                tin = tout = 0
                if tools:
                    convo, tin, tout = _tool_phase(agent, model, convo, tools, cfg)
                # Claude's native JSON output avoids forced-tool errors on Sonnet 5.5.
                method = 'json_schema' if prov == 'anthropic' else 'function_calling'
                runnable = model.with_structured_output(schema, method=method, include_raw=True)
                convo = HOOKS.pre_llm(agent, convo)
                res = runnable.invoke(convo, config=cfg)
                a, b = _usage(res["raw"])
                tin, tout = tin + a, tout + b
                out = res["parsed"]
                if out is None:   # schema-repair retry: show the model its own error
                    if not agent_options.get("schema_repair", True):
                        raise LLMFailure(f"schema mismatch: {res.get('parsing_error')}")
                    err = res.get("parsing_error")
                    convo += [res["raw"] if isinstance(res["raw"], AIMessage) else AIMessage(str(res["raw"])),
                              HumanMessage(f"Your output did not match the schema: {err}. " +
                                           (f"Return JSON matching {schema.__name__} with valid fields." if method == 'json_schema'
                                            else f"Call the {schema.__name__} tool again with valid arguments."))]
                    convo = HOOKS.pre_llm(agent, convo)
                    res = runnable.invoke(convo, config=cfg)
                    a, b = _usage(res["raw"])
                    tin, tout = tin + a, tout + b
                    out = res["parsed"]
                    if out is None:
                        raise LLMFailure(f"schema mismatch: {res.get('parsing_error')}")
                bud.charge(agent, tin, tout, price(prov, tin, tout), prov,
                           (time.perf_counter() - t0) * 1000, fallback=i > 0)
                return _finish(agent, schema, messages, out, prov, meta)
            except (budget_mod.BudgetExceeded, Blocked):
                raise
            except Exception as e:  # noqa: BLE001 — any provider error → retry / next provider
                errors.append(redact_text(f"{prov}#{attempt}: {type(e).__name__}"))
                log.warning("LLM %s via %s failed (attempt %s): %s", redact_text(agent), redact_text(prov), attempt, type(e).__name__)
                time.sleep(min(2 ** attempt, 8) * 0.5)
    raise LLMFailure("; ".join(errors[-6:]) or "no provider available")


def _finish(agent, schema, messages, out, prov, meta):
    out = HOOKS.post_llm(agent, out)
    HOOKS.record("llm", agent, redact([m.content for m in messages]), redact(out), redact({"provider": prov, **(meta or {})}))
    return out


def _tool_phase(agent: str, model, convo: list, tool_names: list[str], cfg: dict):
    """Let the agent call read tools (bounded) before it answers."""
    from odin.tools.registry import REGISTRY

    lc_tools = REGISTRY.langchain_tools(agent, tool_names)
    if not lc_tools:
        return convo, 0, 0
    bound = model.bind_tools(lc_tools)
    tin = tout = 0
    for _ in range(limits()["max_tool_steps"]):
        convo = HOOKS.pre_llm(agent, convo)
        ai = bound.invoke(convo, config=cfg)
        a, b = _usage(ai)
        tin, tout = tin + a, tout + b
        convo.append(ai)
        calls = getattr(ai, "tool_calls", None) or []
        if not calls:
            break
        for tc in calls:
            result = REGISTRY.invoke(agent, tc["name"], tc.get("args") or {})
            rendered = REGISTRY.render(result)
            HOOKS.record("model_context", agent, None, redact_text(rendered), redact({"tool": tc["name"]}))
            convo.append(ToolMessage(content=rendered, tool_call_id=tc["id"]))
    convo.append(HumanMessage("Now produce your final answer using the required output tool."))
    return convo, tin, tout
