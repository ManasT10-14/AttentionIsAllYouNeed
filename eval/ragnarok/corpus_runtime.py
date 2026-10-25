"""Product-side corpus sandbox. This module never reads oracle/.

Only temporary SQLite files under the explicitly supplied workspace are created.
The production DATABASE_URL is not used or changed on disk.
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

_environment = None


def reset_runtime_caches():
    global _environment
    session = sys.modules.get("odin.db.session")
    if session:
        if session.engine.cache_info().currsize:
            session.engine().dispose()
        session._factory.cache_clear()
        session.engine.cache_clear()
    config = sys.modules.get("odin.core.config")
    if config:
        config.settings.cache_clear()
        config.odin_config.cache_clear()
    for module_name in (
        "odin.graphs.analysis",
        "odin.graphs.event",
        "odin.graphs.update",
        "odin.graphs.contract_ws",
    ):
        module = sys.modules.get(module_name)
        if module:
            module.build.cache_clear()
    checkpoint = sys.modules.get("odin.graphs.checkpoint")
    if checkpoint:
        checkpoint.checkpointer.cache_clear()
    budget = sys.modules.get("odin.core.budget")
    if budget:
        budget._budgets.clear()
    if _environment is not None:
        for key, value in _environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        _environment = None


def initialize_workspace(workspace, *, dense=False):
    global _environment
    import yaml

    reset_runtime_caches()
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    repository = Path(__file__).resolve().parents[2]
    config = yaml.safe_load((repository / "backend/config/odin.yaml").read_text(encoding="utf-8"))
    config["retrieval"]["dense_enabled"] = dense
    config["retrieval"]["dense_backend"] = "memory"
    config["email"]["auto_reply_on_reject"] = False
    config_path = workspace / "odin.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    values = {
        "DATABASE_URL": "sqlite:///" + (workspace / "odin.sqlite").as_posix(),
        "ODIN_CONFIG": str(config_path),
        "ODIN_DATA_DIR": str(workspace / "data"),
        "ODIN_CHECKPOINT_BACKEND": "memory",
    }
    _environment = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    # DATA_DIR is resolved on import; update it explicitly if product code was already loaded.
    from odin.core import config as product_config

    product_config.DATA_DIR = workspace / "data"
    service = sys.modules.get("odin.ingest.service")
    if service:
        service.DATA_DIR = product_config.DATA_DIR
    from odin.db.session import engine
    from odin.db.tables import Base, Company
    from sqlalchemy.orm import Session

    Base.metadata.create_all(engine())
    with Session(engine()) as session:
        for cid, name in [
            ("P01", "Aurora Software Private Limited"),
            ("P02", "Forge Electronics Private Limited"),
            ("P03", "Willow Housing Private Limited"),
        ]:
            if session.get(Company, cid) is None:
                session.add(Company(id=cid, name=name, sim_now=date(2027, 1, 15)))
        session.commit()
    return workspace


def seed_documents(corpus_root, contract_ids):
    from odin.ingest.service import ingest_company_context, ingest_contract

    from .corpus import CorpusInputs

    inputs = CorpusInputs(corpus_root)
    context = inputs.input_path("inputs/company_context.md")
    ingest_company_context("P01", context.name, context.read_bytes())
    for contract_id in sorted(contract_ids):
        path = inputs.input_path(f"inputs/contracts/{contract_id}.pdf")
        ingest_contract("P01", path.name, path.read_bytes())


def jsonable(value):
    from dataclasses import asdict, is_dataclass

    def encode(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if is_dataclass(obj):
            return asdict(obj)
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        raise TypeError("Unsupported product serialization")

    return json.loads(json.dumps(value, default=encode))
