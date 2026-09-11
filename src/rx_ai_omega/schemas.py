from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import ApprovalStatus, MissionStatus, Role, StepStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=200)
    role: Role = Role.viewer


class UserRead(ORMModel):
    id: str
    username: str
    role: Role
    active: bool
    created_at: datetime


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    instructions: str = Field(min_length=1, max_length=20_000)
    provider: str | None = Field(default=None, pattern=r"^(mock|openai|ollama)$")


class AgentRead(ORMModel):
    id: str
    name: str
    instructions: str
    provider: str | None
    enabled: bool
    created_at: datetime


class StepCreate(BaseModel):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    agent_id: str
    prompt: str = Field(min_length=1, max_length=50_000)
    depends_on: list[str] = Field(default_factory=list)
    risk: str = Field(default="low", pattern=r"^(low|medium|high)$")
    action: str = Field(default="analysis", max_length=50)


class MissionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=50_000)
    steps: list[StepCreate] = Field(min_length=1, max_length=100)


class StepRead(ORMModel):
    id: str
    key: str
    position: int
    agent_id: str
    prompt: str
    depends_on: list[str]
    risk: str
    action: str
    status: StepStatus
    output: str | None
    error: str | None


class MissionRead(ORMModel):
    id: str
    title: str
    objective: str
    status: MissionStatus
    created_by_id: str
    created_at: datetime
    updated_at: datetime
    steps: list[StepRead]


class ApprovalDecision(BaseModel):
    note: str | None = Field(default=None, max_length=2_000)


class ApprovalRead(ORMModel):
    id: str
    mission_id: str
    step_id: str
    status: ApprovalStatus
    reason: str
    requested_at: datetime
    decided_at: datetime | None
    decided_by_id: str | None
    decision_note: str | None


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=1_000_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRead(ORMModel):
    id: str
    title: str
    content: str
    metadata_json: dict[str, Any]
    created_at: datetime


class SearchHit(BaseModel):
    document_id: str
    title: str
    score: float
    excerpt: str


class AuditRead(ORMModel):
    id: str
    actor_id: str | None
    action: str
    resource_type: str
    resource_id: str
    details: dict[str, Any]
    created_at: datetime
