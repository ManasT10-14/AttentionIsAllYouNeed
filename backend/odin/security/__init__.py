"""Runtime security suite, attached through odin.core.hooks.HOOKS (see guard.py)."""
from __future__ import annotations

from odin.security.guard import SecurityGuard, detect, neutralize, redact  # noqa: F401


def install() -> SecurityGuard | None:
    """Register the guard once when `security.enabled` (default true) in odin.yaml."""
    from odin.core.config import odin_config
    from odin.core.hooks import HOOKS
    cfg = odin_config().get("security") or {}
    if not cfg.get("enabled", True):
        return None
    existing = next((g for g in HOOKS.guards if isinstance(g, SecurityGuard)), None)
    if existing:
        return existing
    guard = SecurityGuard(cfg)
    HOOKS.guards.append(guard)
    HOOKS.evals.append(guard)      # records registry denials (allowlist / approval) as security events
    return guard
