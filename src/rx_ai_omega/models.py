import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(str, enum.Enum):
    viewer = "viewer"
    operator = "operator"
    admin = "admin"


class MissionStatus(str, enum.Enum):
    draft = "draft"
    queued = "queued"
    running = "running"
    waiting_approval = "waiting_approval"
    completed = "completed"
    failed = "failed"
    rejected = "rejected"


class StepStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    waiting_approval = "waiting_approval"
    completed = "completed"
    failed = "failed"
    rejected = "rejected"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.viewer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    instructions: Mapped[str] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(30), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200))
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[MissionStatus] = mapped_column(Enum(MissionStatus), default=MissionStatus.draft, index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    steps: Mapped[list["WorkflowStep"]] = relationship(back_populates="mission", cascade="all, delete-orphan", order_by="WorkflowStep.position")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (UniqueConstraint("mission_id", "key", name="uq_step_mission_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    position: Mapped[int]
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    prompt: Mapped[str] = mapped_column(Text)
    depends_on: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk: Mapped[str] = mapped_column(String(20), default="low")
    action: Mapped[str] = mapped_column(String(50), default="analysis")
    status: Mapped[StepStatus] = mapped_column(Enum(StepStatus), default=StepStatus.pending)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mission: Mapped[Mission] = relationship(back_populates="steps")
    agent: Mapped[Agent] = relationship()


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[str] = mapped_column(ForeignKey("workflow_steps.id", ondelete="CASCADE"), unique=True)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), default=ApprovalStatus.pending)
    reason: Mapped[str] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Handoff(Base):
    __tablename__ = "handoffs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True)
    from_step_id: Mapped[str] = mapped_column(ForeignKey("workflow_steps.id"))
    to_step_id: Mapped[str] = mapped_column(ForeignKey("workflow_steps.id"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str] = mapped_column(String(36), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
