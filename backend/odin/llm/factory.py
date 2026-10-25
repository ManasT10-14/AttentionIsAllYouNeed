"""Provider registry: bedrock (OpenAI-compatible) → openai → anthropic → groq, per config/odin.yaml."""
from __future__ import annotations

from functools import lru_cache

from odin.core.config import odin_config, settings


def provider_cfg(name: str) -> dict:
    return odin_config()["providers"][name]


def provider_available(name: str) -> bool:
    cfg = provider_cfg(name)
    if cfg["kind"] == "fake":
        return True
    if not cfg.get("api_key") or not cfg.get("model"):
        return False
    return cfg["kind"] != "openai" or name != "bedrock" or bool(cfg.get("base_url"))


def chain_for(agent: str) -> list[str]:
    """Ordered provider names to try for an agent, skipping ones without credentials."""
    forced = settings().odin_force_provider
    if forced:
        return [forced]
    conf = odin_config()
    a = {**conf["defaults"], **(conf["agents"].get(agent) or {})}
    order = [a["provider"], *[p for p in a.get("fallback", []) if p != a["provider"]]]
    avail = [p for p in order if provider_available(p)]
    return avail or ["fake"]


def model_for(agent: str, provider: str) -> str | None:
    """Per-agent model override, e.g. agents: {thor: {models: {bedrock: moonshotai.kimi-k2.5}}}."""
    return ((odin_config()["agents"].get(agent) or {}).get("models") or {}).get(provider)


@lru_cache(maxsize=64)
def chat_model(name: str, temperature: float = 0.0, model: str | None = None):
    cfg = {**provider_cfg(name), **({"model": model} if model else {})}
    kind = cfg["kind"]
    common = dict(temperature=temperature, max_retries=0, timeout=120)
    if kind == "openai":
        from langchain_openai import ChatOpenAI
        kw = dict(model=cfg["model"], api_key=cfg["api_key"], seed=7, **common)
        if cfg.get("base_url"):
            kw["base_url"] = cfg["base_url"]
        if cfg.get("project"):                       # sends OpenAI-Project header (Bedrock Mantle)
            kw["default_headers"] = {"OpenAI-Project": cfg["project"]}
        return ChatOpenAI(**kw)
    if kind == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=cfg["model"], api_key=cfg["api_key"], max_tokens=8192, **common)
    if kind == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=cfg["model"], api_key=cfg["api_key"], **common)
    raise ValueError(f"no chat model for provider kind {kind}")


def price(name: str, tokens_in: int, tokens_out: int) -> float:
    p = provider_cfg(name).get("price_per_mtok") or {}
    return (tokens_in * p.get("in", 0) + tokens_out * p.get("out", 0)) / 1_000_000
