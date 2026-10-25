"""Graph state schemas (NFR1: agents communicate through a defined state + message structure).
Heavy artefacts live in the shared store (db/repo.py); state carries ids, counters and routing info."""
from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict


class WSState(TypedDict, total=False):
    company_id: str
    run_id: str
    scenario_id: Optional[str]
    contract_id: str                 # or "cross"
    version: int
    mode: str                        # analysis | update
    force: bool
    focus_clauses: list[str]
    clarify_round: int
    debate_round: int
    disputed: list[str]
    budget_hit: str
    errors: Annotated[list[str], operator.add]
    ws_results: Annotated[list[dict], operator.add]


class AnalysisState(TypedDict, total=False):
    company_id: str
    run_id: str
    scenario_id: Optional[str]
    contract_ids: list[str]
    force: bool
    ws_results: Annotated[list[dict], operator.add]
    errors: Annotated[list[str], operator.add]
    final_status: str


class EventState(TypedDict, total=False):
    company_id: str
    run_id: str
    scenario_id: Optional[str]
    event_id: str
    contract_ids: list[str]
    affected_clauses: list[dict]
    mapping: dict
    violation_ids: list[str]
    finding_ids: list[str]
    noise: bool
    disputed: list[str]
    debate_round: int
    budget_hit: str
    errors: Annotated[list[str], operator.add]


class UpdateState(TypedDict, total=False):
    company_id: str
    run_id: str
    scenario_id: Optional[str]
    contract_id: str
    from_version: int
    to_version: int
    changes: list[dict]
    touched: list[str]
    ws_results: Annotated[list[dict], operator.add]
    errors: Annotated[list[str], operator.add]
