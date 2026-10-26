"""Inspectable control scope. Loaded controls are never a security certification."""
import os

from fastapi import APIRouter, Depends
from odin.api.deps import current_user
from odin.api.responses import PrivateAPIRoute, RedactedJSONResponse
from odin.core.context import run_ctx
from odin.core.hooks import HOOKS
from odin.db import repo
from odin.db.session import db
from odin.db.tables import ToolCall, User
from odin.security.guard import SecurityGuard
from sqlalchemy import select

router = APIRouter(default_response_class=RedactedJSONResponse, route_class=PrivateAPIRoute)


@router.get("/security/status", tags=["security"])
def status(u: User = Depends(current_user)):
    guard = next((g for g in HOOKS.guards if isinstance(g, SecurityGuard)), None)
    with run_ctx(u.company_id):
        decisions = repo.query("security_event", limit=500)
    audit_status = "readable"
    try:
        with db() as session:
            session.scalar(select(ToolCall.id).where(ToolCall.company_id == u.company_id).limit(1))
    except Exception:
        audit_status = "unavailable"
    controlled = "enforced" if guard else "disabled"
    return {
        "policy_version": "security-v2",
        "guard_enabled": bool(guard),
        "classifier": {"enabled": bool(guard and guard.classifier),
                       "status": "configured_unverified" if guard and guard.classifier else "disabled"},
        "trace_privacy_mode": "redacted" if os.getenv("ODIN_TRACE_CONTENT", "").lower() == "redacted" else "metadata_only",
        "last_decision_at": max((d.get("created_at", "") for d in decisions), default=None),
        "audit_sink": {"status": audit_status, "scope": "readability only; write delivery is not monitored"},
        "protected_surfaces": [
            {"name": "email_intake", "status": controlled, "detail": "Headers/body scanned before parsing, clock or reply"},
            {"name": "scheduled_events", "status": controlled, "detail": "Delivery-time check; holds pause replay before clock/model effects"},
            {"name": "model_inputs", "status": controlled, "detail": "Every structured/tool/repair invoke; untrusted text handling and redaction"},
            {"name": "model_outputs", "status": controlled, "detail": "Structured response secret checks; unsafe schema rewrites blocked"},
            {"name": "tool_execution", "status": "enforced", "detail": "Allowlist, tenant context, bound approval and one-shot execution claim"},
            {"name": "api_json", "status": "enforced", "detail": "Recursive credential redaction on product JSON and SSE"},
            {"name": "exports", "status": "enforced", "detail": "Generated HTML/PDF/CSV/calendar redaction; original files remain authorized source evidence"},
        ],
        "limitations": [
            "Rule matches and text wrapping do not prove prompt injection cannot succeed.",
            "Tests use synthetic canaries and blocked external effects; no live provider or cloud trace certification.",
            "Interrupted release/execution claims require manual recovery; no durable outbox worker is installed.",
            "OCR/binary attachment semantics and all deployment controls are not certified by this status endpoint.",
            "Remote trace upload and audit write success are separate from configuration/readability.",
        ],
    }
