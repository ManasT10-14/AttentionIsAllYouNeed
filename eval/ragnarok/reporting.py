"""Redacted atomic JSON output and conservative CI status aggregation."""

import json
import os
import re
import tempfile
from pathlib import Path

from .models import RunReport
from .privacy import redact as shared_redact

STATUSES = ("passed", "failed", "error", "skipped", "invalid")
def redact(value, secrets=()):
    """Shared credential policy with legacy export markers; retain PII for evidence review.

    This adapter runs after scoring. Explicit case canaries and environment literals are
    redacted even when they do not resemble a provider credential.
    """
    def legacy_markers(item):
        if isinstance(item, str):
            return re.sub(r"\[REDACTED(?::[^\]]+)?\]", "[REDACTED]", item)
        if isinstance(item, dict):
            return {legacy_markers(key): legacy_markers(value) for key, value in item.items()}
        if isinstance(item, (list, tuple)):
            return [legacy_markers(value) for value in item]
        return item
    return legacy_markers(shared_redact(value, pii=False, secrets=secrets))


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
