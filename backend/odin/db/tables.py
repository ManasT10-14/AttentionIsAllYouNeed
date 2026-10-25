"""Postgres schema. Agent outputs live in `records` (typed by `kind`, payload = pydantic JSON)
so the shared store is explicit and queryable (NFR6) without a table per model."""
from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

EMBED_DIM = 384  # BAAI/bge-small-en-v1.5

J = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, default="")
    context: Mapped[dict] = mapped_column(J, default=dict)
    sim_now: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    email: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String, default="")
    google_sub: Mapped[str | None] = mapped_column(String, nullable=True)
    gmail_address: Mapped[str | None] = mapped_column(String, nullable=True)   # inbox Heimdall watches
    role: Mapped[str] = mapped_column(String, default="admin")   # admin now; super_admin later
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    enc_refresh: Mapped[str] = mapped_column(Text, default="")
    enc_access: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scopes: Mapped[str] = mapped_column(Text, default="")
    last_poll_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (UniqueConstraint("company_id", "contract_id"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    contract_id: Mapped[str] = mapped_column(String)            # CONTRACT ID from cover
    title: Mapped[str] = mapped_column(String, default="")
    type: Mapped[str] = mapped_column(String, default="other")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    meta: Mapped[dict] = mapped_column(J, default=dict)          # CoverMeta of current version
    status: Mapped[str] = mapped_column(String, default="ingested")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ContractVersion(Base):
    __tablename__ = "contract_versions"
    __table_args__ = (UniqueConstraint("company_id", "contract_id", "version"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(String)
    contract_id: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer)
    file_path: Mapped[str] = mapped_column(Text)
    pdf_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    cover: Mapped[dict] = mapped_column(J, default=dict)
    parse_warnings: Mapped[list] = mapped_column(J, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClauseRow(Base):
    __tablename__ = "clauses"
    __table_args__ = (Index("ix_clause_lookup", "company_id", "contract_id", "version", "number"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(String, index=True)
    contract_id: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    number: Mapped[str] = mapped_column(String)
    heading: Mapped[str] = mapped_column(Text, default="")
    text: Mapped[str] = mapped_column(Text)
    clause_type: Mapped[str] = mapped_column(String, default="general")
    page: Mapped[int] = mapped_column(Integer, default=1)
    char_start: Mapped[int] = mapped_column(Integer, default=0)
    char_end: Mapped[int] = mapped_column(Integer, default=0)
    bboxes: Mapped[list] = mapped_column(J, default=list)        # [[page, x0,y0,x1,y1], ...]
    embedding = mapped_column(Vector(EMBED_DIM), nullable=True)


class Record(Base):
    """Every agent artefact: extraction, finding, verification, ruling, violation, action, alert,
    event, dependency, report, clarification. `data` is the pydantic model dump."""
    __tablename__ = "records"
    __table_args__ = (Index("ix_records_kind", "company_id", "kind", "scenario_id"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    contract_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    scenario_id: Mapped[str | None] = mapped_column(String, nullable=True)   # what-if sandbox
    status: Mapped[str] = mapped_column(String, default="")
    data: Mapped[dict] = mapped_column(J, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String)                   # analysis | event | update | whatif | ask
    status: Mapped[str] = mapped_column(String, default="running")   # running | done | partial | failed
    workplan: Mapped[dict] = mapped_column(J, default=dict)
    budget: Mapped[dict] = mapped_column(J, default=dict)
    trace_url: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    scenario_id: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentMessageRow(Base):
    __tablename__ = "agent_messages"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(String, index=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    sender: Mapped[str] = mapped_column(String)
    receiver: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(J, default=dict)
    contract_id: Mapped[str | None] = mapped_column(String, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ToolCall(Base):
    """Audit trail of every tool invocation (security-suite friendly)."""
    __tablename__ = "tool_calls"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(String, index=True)
    run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    agent: Mapped[str] = mapped_column(String)
    tool: Mapped[str] = mapped_column(String)
    scope: Mapped[str] = mapped_column(String)
    args: Mapped[dict] = mapped_column(J, default=dict)
    result_summary: Mapped[str] = mapped_column(Text, default="")
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_ms: Mapped[float] = mapped_column(Float, default=0)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
