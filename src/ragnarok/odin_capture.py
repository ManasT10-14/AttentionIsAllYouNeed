"""Request-scoped Odin hook collection; no dependency on Odin at import time."""

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock

from .models import Citation, Document, Evidence, ExecutionResult, ToolEvent, WorkflowEvent


@dataclass
class Capture:
    max_records: int = 10000
    max_bytes: int = 16_000_000
    records: list[dict] = field(default_factory=list)
    truncated: bool = False
    _bytes: int = 0
    _lock: Lock = field(default_factory=Lock)

    def record(self, kind, agent, inputs, output, meta):
        def encode(obj):
            return obj.model_dump(mode="json") if hasattr(obj, "model_dump") else str(obj)

        with self._lock:
            if self.truncated:
                return
            try:
                serialized = json.dumps(
                    dict(kind=kind, agent=agent, inputs=inputs, output=output, meta=meta),
                    default=encode,
                )
                size = len(serialized.encode())
                if len(self.records) >= self.max_records or self._bytes + size > self.max_bytes:
                    self.truncated = True
                    return
                self.records.append(json.loads(serialized))
                self._bytes += size
            except Exception:
                self.truncated = True


@contextmanager
def capture(*, max_records=10000):
    from odin.core.hooks import subscribe

    observed = Capture(max_records=max_records)
    with subscribe(observed):
        yield observed


class EvaluationGuard:
    """Evaluation-only fence. Not a general prompt-injection classifier."""

    def __init__(self, *, allow_internal_writes=False):
        self.allow_internal_writes = allow_internal_writes

    def pre_tool(self, agent, tool, scope, args):
        if scope in {"external_send", "file_write"} or (
            scope == "write_state" and not self.allow_internal_writes
        ):
            from odin.core.hooks import Blocked

            raise Blocked("External effects are disabled in the evaluation worker")
        return args


def clause_id(record):
    return f"{record['contract_id']}:v{record['version']}:{record['clause_number']}"


def normalize(observed: Capture, output, *, operation: str) -> ExecutionResult:
    state = "partial" if observed.truncated else "complete"
    records = observed.records
    retrievals = [r for r in records if r["kind"] == "retrieval"]
    raw_docs = [doc for record in retrievals for doc in record["output"]]
    direct_documents = [r["output"] for r in records if r["kind"] == "document"]
    all_observed = [*raw_docs, *direct_documents]
    if operation not in {"ask", "retrieval"}:
        raw_docs += direct_documents
    # Ask's supplied passages are the actual context, not every retrieval candidate.
    if operation == "ask" and isinstance(output, dict) and "passages" in output:
        raw_docs = output["passages"]

    def documents(rows):
        docs, seen = [], set()
        for doc in rows:
            identity = clause_id(doc)
            # Retain differing tenant ownership even if a malformed source reuses IDs.
            key = (identity, doc.get("company_id"))
            if key not in seen:
                docs.append(
                    Document(
                        id=identity,
                        text=doc["text"],
                        tenant_id=doc.get("company_id"),
                        clause_id=doc["clause_number"],
                    )
                )
                seen.add(key)
        return docs

    context_available = operation == "ask" and isinstance(output, dict) and "passages" in output
    model_context = [d["text"] for d in output["passages"]] if context_available else []
    model_context.extend(r["output"] for r in records if r["kind"] == "model_context")
    tools, events, errors = [], [], []
    for record in records:
        kind, meta = record["kind"], record["meta"]
        if kind == "tool":
            attempted = meta.get("executed", False)
            phase = ("executed" if meta.get("ok") else "failed") if attempted else "requested"
            tools.append(
                ToolEvent(
                    name=meta["tool"],
                    actor=record["agent"],
                    arguments=record["inputs"],
                    phase=phase,
                    authorized=meta.get("authorized"),
                    approved=meta.get("approved"),
                    error=meta.get("error_type") if attempted else None,
                )
            )
        elif kind in {"agent", "message"}:
            events.append(
                WorkflowEvent(
                    kind=meta.get("event", kind), actor=record["agent"], target=meta.get("target")
                )
            )
            if meta.get("failed"):
                errors.append("An agent reported incomplete execution")
    if isinstance(output, dict) and output.get("errors"):
        errors.append("The graph returned errors")
    if isinstance(output, dict) and output.get("final_status") in {"partial", "failed"}:
        errors.append("The graph did not complete successfully")
    if errors:
        state = "partial"
    citations = []

    def walk(value):
        if isinstance(value, dict):
            if {"contract_id", "clause_number", "quote"} <= value.keys() and value.get("quote"):
                version = value.get("version")
                candidates = [
                    d
                    for d in all_observed
                    if d["contract_id"] == value["contract_id"]
                    and d["clause_number"] == value["clause_number"]
                ]
                if version is None and len({d["version"] for d in candidates}) == 1:
                    version = candidates[0]["version"]
                identity = f"{value['contract_id']}:v{version}:{value['clause_number']}"
                citations.append(
                    Citation(
                        document_id=identity, clause_id=value["clause_number"], quote=value["quote"]
                    )
                )
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(output)
    # Graph state does not include all persisted artefacts; do not claim a complete citation set.
    citation_state = "complete" if operation == "ask" else "partial"
    return ExecutionResult(
        output=output.get("answer") if operation == "ask" and isinstance(output, dict) else output,
        state=state,
        documents=Evidence(
            state=("partial" if observed.truncated else "complete")
            if retrievals or direct_documents
            else "unavailable",
            items=documents(raw_docs),
        ),
        observed_documents=Evidence(
            state=("partial" if observed.truncated else "complete")
            if retrievals or direct_documents
            else "unavailable",
            items=documents(all_observed),
        ),
        model_context=Evidence(
            state=("partial" if observed.truncated else "complete")
            if context_available or model_context
            else "unavailable",
            items=model_context,
        ),
        tools=Evidence(state="partial" if observed.truncated else "complete", items=tools),
        events=Evidence(state="partial" if observed.truncated else "complete", items=events),
        citations=Evidence(
            state="partial" if observed.truncated else citation_state, items=citations
        ),
        errors=errors,
        metadata={
            "operation": operation,
            "observation_truncated": observed.truncated,
            "insufficient_evidence": output.get("insufficient_evidence")
            if isinstance(output, dict)
            else None,
            "tool_decisions": [r["meta"] for r in records if r["kind"] == "tool"],
            "providers": sorted(
                {r["meta"].get("provider", "unknown") for r in records if r["kind"] == "llm"}
            ),
        },
    )
