"""Product compatibility facade for the canonical shared privacy policy.

The standalone evaluator ships ragnarok.privacy; runtime, telemetry and report exports
all use these exact functions. Keep original imports working at this module path.
"""
from ragnarok.privacy import (
    PII_PATTERNS as PII_PATTERNS,
)
from ragnarok.privacy import (
    SECRET_PATTERNS as SECRET_PATTERNS,
)
from ragnarok.privacy import (
    _env_secrets as _env_secrets,
)
from ragnarok.privacy import (
    _luhn as _luhn,
)
from ragnarok.privacy import (
    join_text_blocks as join_text_blocks,
)
from ragnarok.privacy import (
    redact as redact,
)
from ragnarok.privacy import (
    redact_text as redact_text,
)
from ragnarok.privacy import (
    redact_with_rules as redact_with_rules,
)
