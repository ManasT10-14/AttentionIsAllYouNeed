"""Dataset parsing with file-local validation errors."""

import json
from pathlib import Path

from .models import Dataset


def load_dataset(path: str | Path) -> Dataset:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        # Omitted kind means an ordinary quality case.
        if isinstance(raw, dict) and isinstance(raw.get("cases"), list):
            for case in raw["cases"]:
                if isinstance(case, dict):
                    case.setdefault("kind", "quality")
        return Dataset.model_validate(raw)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Invalid dataset {path}: {exc}") from exc
