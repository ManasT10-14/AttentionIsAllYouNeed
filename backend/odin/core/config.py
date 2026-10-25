"""Env settings + config/odin.yaml loader (with ${VAR} expansion)."""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]          # RAGNAROK/
DATA_DIR = Path(os.getenv("ODIN_DATA_DIR", ROOT / "data"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://odin:odin@localhost:5432/odin"
    secret_key: str = "change-me"
    fernet_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    public_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    dev_login: bool = True
    webhook_url: str = ""
    odin_force_provider: str = ""
    odin_config: str = str(ROOT / "config" / "odin.yaml")


@lru_cache
def settings() -> Settings:
    from dotenv import load_dotenv
    # A real dotenv parser preserves quoting/comments and empty credentials.
    # Existing shell settings win; both provider expansion and SDKs see values.
    load_dotenv(ROOT / ".env", override=False)
    return Settings(_env_file=ROOT / ".env")


_VAR = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand(obj):
    if isinstance(obj, str):
        return _VAR.sub(lambda m: os.getenv(m.group(1), ""), obj)
    if isinstance(obj, dict):
        return {k: _expand(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand(v) for v in obj]
    return obj


@lru_cache
def odin_config() -> dict:
    settings()
    with open(settings().odin_config, encoding="utf-8") as f:
        return _expand(yaml.safe_load(f))


def limits() -> dict:
    return odin_config()["limits"]
