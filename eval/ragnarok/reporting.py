"""Redacted atomic JSON output and conservative CI status aggregation."""

import json
import os
import re
import tempfile
from pathlib import Path

from .models import RunReport

STATUSES = ("passed", "failed", "error", "skipped", "invalid")
SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "password",
    "secret",
    "access_token",
    "refresh_token",
    "cookie",
    "set-cookie",
    "x-api-key",
}
KEY_PATTERN = re.compile(r"\b(?:lsv2_[A-Za-z0-9_-]{10,}|sk-[A-Za-z0-9_-]{12,})\b")
BEARER_PATTERN = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)


def redact(value, secrets=()):
    if isinstance(value, dict):
        return {
            redact(key, secrets): "[REDACTED]"
            if key.lower() in SENSITIVE_KEYS
            else redact(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in sorted(set(secrets), key=len, reverse=True):
            if secret:
                value = re.sub(re.escape(secret), "[REDACTED]", value, flags=re.IGNORECASE)
        return BEARER_PATTERN.sub("Bearer [REDACTED]", KEY_PATTERN.sub("[REDACTED]", value))
    return value


def exit_code(cases) -> int:
    checks = [check for case in cases for check in case.checks]
    if any(check.status in {"error", "invalid"} for check in checks):
        return 2
    if any(check.status == "failed" for check in checks):
        return 1
    if not any(check.status == "passed" for check in checks):
        return 3
    if any(check.required and check.status == "skipped" for check in checks):
        return 3
    return 0


def write_report(report: RunReport, path: str | Path) -> None:
    """Persist observations with known secrets masked; free text can still contain PII."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = redact(report.model_dump(mode="json"), report._redaction_values)
    encoded = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = stream.name
            stream.write(encoded)
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
