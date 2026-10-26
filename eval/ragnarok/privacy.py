"""Shared, non-mutating privacy policy for outbound data and persisted diagnostics.

Contact addresses remain usable evidence. This masks credentials and selected identifiers;
it does not make private contract text suitable for remote publication.
"""
from __future__ import annotations

import os
import re

from pydantic import BaseModel

_I = re.IGNORECASE
_SENSITIVE_KEY = re.compile(
    r"(?:^|_)(?:password|passwd|pwd|secret|token|api_key|apikey|authorization|"
    r"private_key|credentials?|cookies?|fernet_key|client_secret|connection_string)(?:$|_)", _I)
SECRET_PATTERNS = [
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----")),
    ("api_key", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gsk_[A-Za-z0-9_-]{12,}|lsv2_[A-Za-z0-9_-]{10,}|"
                           r"AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|"
                           r"AIza[0-9A-Za-z_-]{20,})\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", _I)),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")),
    ("url_credentials", re.compile(r"(?<=://)[^\s/@:]+:[^\s/@]+@")),
    ("credential", re.compile(r"\b(password|passwd|pwd|api[_ -]?key|secret|(?:access[_ -]?)?token|"
                              r"client[_ -]?secret)\s*[\"']?\s*[:=]\s*[\"']?(?!\[REDACTED)[^\s,;\"'&<>}]+", _I)),
]
PII_PATTERNS = [
    ("card_number", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("us_ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("aadhaar", re.compile(r"(?<!\d\s)(?<!\d)[2-9]\d{3}\s\d{4}\s\d{4}(?!\s?\d)")),
]


def _sensitive(key):
    key = re.sub(r"([a-z])([A-Z])", r"\1_\2", str(key))
    return bool(_SENSITIVE_KEY.search(re.sub(r"[^\w]", "_", key)))


def _env_secrets():
    return sorted({value for key, value in os.environ.items()
                   if (_sensitive(key) or "FERNET" in key.upper()) and value and len(value) >= 8})


def _luhn(digits):
    return sum(x if i % 2 == 0 else x * 2 - 9 if x > 4 else x * 2
               for i, x in enumerate(map(int, digits[::-1]))) % 10 == 0


def redact_with_rules(text: str, pii: bool = True, *, secrets=(), _env_values=None) -> tuple[str, list[str]]:
    found = []
    for value in sorted(_env_secrets() if _env_values is None else _env_values, key=len, reverse=True):
        if value in text:
            text = text.replace(value, "[REDACTED:env_secret]")
            found.append("env_secret")
    for value in sorted({item for item in secrets if isinstance(item, str) and item}, key=len, reverse=True):
        text, count = re.subn(re.escape(value), "[REDACTED:configured_secret]", text, flags=re.IGNORECASE)
        if count:
            found.append("configured_secret")
    for name, pattern in SECRET_PATTERNS + (PII_PATTERNS if pii else []):
        def replace(match, name=name):
            if name == "card_number":
                digits = re.sub(r"\D", "", match.group())
                if not (13 <= len(digits) <= 19 and _luhn(digits)):
                    return match.group()
            found.append(name)
            prefix = match.group(1) + ": " if name == "credential" else ""
            return prefix + f"[REDACTED:{name}]"
        text = pattern.sub(replace, text)
    return text, found


def redact_text(text: str, *, pii: bool = True, secrets=(), _env_values=None) -> str:
    return redact_with_rules(text, pii, secrets=secrets, _env_values=_env_values)[0]


def join_text_blocks(blocks, *, strings=False):
    """Join adjacent text blocks before inspection so fragmentation cannot hide a credential.

    Preserve block count, ancillary fields, and non-text block order. Only transient outbound
    copies are passed here; original evidence is never modified.
    """
    result = []
    first = None
    def get_text(block):
        if isinstance(block, str):
            return block
        return block["text"]
    def set_text(block, text):
        return text if isinstance(block, str) else {**block, "text": text}
    for block in blocks:
        if ((strings and isinstance(block, str)) or
                (isinstance(block, dict) and block.get("type") in {"text", "input_text", "output_text"}
                 and isinstance(block.get("text"), str))):
            if first is None:
                first = len(result)
                result.append(set_text(block, get_text(block)))
            else:
                result[first] = set_text(result[first], get_text(result[first]) + get_text(block))
                result.append(set_text(block, ""))
        else:
            first = None
            result.append(block)
    return result


def redact(value, *, pii: bool = True, secrets=(), _env_values=None):
    """Redact recursively, preserving model/container types and the original value."""
    # Snapshot per boundary, not per leaf; large reports otherwise block API responses.
    env_values = _env_secrets() if _env_values is None else _env_values
    secrets = tuple(item for item in secrets if isinstance(item, str) and item)
    if isinstance(value, str):
        return redact_text(value, pii=pii, secrets=secrets, _env_values=env_values)
    if isinstance(value, BaseModel):
        return value.model_copy(update=redact(dict(value), pii=pii, secrets=secrets, _env_values=env_values))
    if isinstance(value, dict):
        return {redact_text(key, pii=pii, secrets=secrets, _env_values=env_values) if isinstance(key, str) else key:
                "[REDACTED:sensitive_key]" if _sensitive(key) and item is not None
                else redact(join_text_blocks(item, strings=True)
                            if key == "content" and isinstance(item, list) else item,
                            pii=pii, secrets=secrets, _env_values=env_values)
                for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        items = [redact(item, pii=pii, secrets=secrets, _env_values=env_values) for item in join_text_blocks(value)]
        return tuple(items) if isinstance(value, tuple) else items
    return value
