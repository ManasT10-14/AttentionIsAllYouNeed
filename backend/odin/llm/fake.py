"""Offline stand-in for an LLM: builds the smallest valid instance of the requested schema.
Lets the whole graph run (tests, no-key demos) without network. Never used when a real key exists."""
from __future__ import annotations

import types
import typing
from datetime import date, datetime
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined


def fake_value(tp: Any, meta: list | None = None) -> Any:
    origin = get_origin(tp)
    if origin in (Union, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        return None if len(args) < len(get_args(tp)) else fake_value(args[0])
    if origin is Literal:
        return get_args(tp)[0]
    if origin in (list, typing.List):
        return []
    if origin in (dict, typing.Dict):
        return {}
    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return fake_instance(tp)
    lo = None
    for m in meta or []:
        lo = getattr(m, "ge", None) or getattr(m, "gt", None) or lo
    if tp is bool:
        return False
    if tp is int:
        return int(lo or 1)
    if tp is float:
        return float(lo or 0.5)
    if tp is str:
        return "n/a"
    if tp is date:
        return date.today()
    if tp is datetime:
        return datetime.utcnow()
    return None


def fake_instance(model: type[BaseModel]) -> BaseModel:
    kw = {}
    for name, f in model.model_fields.items():
        if f.default is not PydanticUndefined or f.default_factory is not None:
            continue
        kw[name] = fake_value(f.annotation, f.metadata)
    return model.model_validate(kw)
