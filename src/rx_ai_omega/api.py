from typing import Annotated, TypeAlias

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from .audit import record_audit
from .config import get_settings
from .database import SessionLocal, get_db
from .kernel import Kernel
from .memory import build_memory
from .models import (
    Agent,
    Approval,
    ApprovalStatus,
    AuditEvent,
    Document,
    Mission,
    MissionStatus,
    StepStatus,
    User,
    WorkflowStep,
    utcnow,
)
from .planning import InvalidPlan, validate_and_order
from .queueing import MissionQueue
from .schemas import (
    AgentCreate,
    AgentRead,
    ApprovalDecision,
    ApprovalRead,
    AuditRead,
    DocumentCreate,
    DocumentRead,
    MissionCreate,
    MissionRead,
    SearchHit,
    Token,
    UserCreate,
    UserRead,
)
from .security import Admin, CurrentUser, Operator, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api")
Db: TypeAlias = Annotated[Session, Depends(get_db)]


def load_mission(db: Session, mission_id: str) -> Mission:
    mission = db.scalar(
        select(Mission)
        .where(Mission.id == mission_id)
        .options(selectinload(Mission.steps))
    )
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


def run_local(mission_id: str) -> None:
    with SessionLocal() as db:
        Kernel(get_settings()).execute(db, mission_id)


def enqueue_mission(mission_id: str, background_tasks: BackgroundTasks) -> None:
    try:
        MissionQueue(get_settings()).enqueue(mission_id, background_tasks, run_local)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/auth/token", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: Db) -> Token:
    user = db.scalar(select(User).where(User.username == form.username))
    if user is None or not user.active or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    record_audit(db, "auth.login", "user", user.id, actor_id=user.id)
    db.commit()
    return Token(access_token=create_access_token(user))


@router.get("/auth/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user


@router.get("/users", response_model=list[UserRead])
def list_users(db: Db, _admin: Admin) -> list[User]:
    return list(db.scalars(select(User).order_by(User.username)).all())


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(body: UserCreate, db: Db, admin: Admin) -> User:
    if db.scalar(select(User.id).where(User.username == body.username)):
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(username=body.username, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.flush()
    record_audit(db, "user.created", "user", user.id, admin.id, {"role": user.role.value})
    db.commit()
    db.refresh(user)
    return user


@router.get("/agents", response_model=list[AgentRead])
def list_agents(db: Db, _user: CurrentUser) -> list[Agent]:
    return list(db.scalars(select(Agent).order_by(Agent.name)).all())


@router.post("/agents", response_model=AgentRead, status_code=201)
def create_agent(body: AgentCreate, db: Db, operator: Operator) -> Agent:
    if db.scalar(select(Agent.id).where(Agent.name == body.name)):
        raise HTTPException(status_code=409, detail="Agent name already exists")
    agent = Agent(**body.model_dump())
    db.add(agent)
    db.flush()
    record_audit(db, "agent.created", "agent", agent.id, operator.id)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/missions", response_model=list[MissionRead])
def list_missions(db: Db, _user: CurrentUser) -> list[Mission]:
    statement = select(Mission).options(selectinload(Mission.steps)).order_by(desc(Mission.created_at))
    return list(db.scalars(statement).unique().all())


@router.get("/missions/{mission_id}", response_model=MissionRead)
def get_mission(mission_id: str, db: Db, _user: CurrentUser) -> Mission:
    return load_mission(db, mission_id)


@router.post("/missions", response_model=MissionRead, status_code=201)
def create_mission(body: MissionCreate, db: Db, operator: Operator) -> Mission:
    try:
        order = validate_and_order(body.steps)
    except InvalidPlan as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    agents = {
        agent.id: agent
        for agent in db.scalars(select(Agent).where(Agent.id.in_({step.agent_id for step in body.steps}))).all()
    }
    missing = {step.agent_id for step in body.steps} - set(agents)
    if missing:
        raise HTTPException(status_code=422, detail=f"Unknown or unavailable agent IDs: {sorted(missing)}")
    if any(not agent.enabled for agent in agents.values()):
        raise HTTPException(status_code=422, detail="Disabled agents cannot be assigned")
    by_key = {step.key: step for step in body.steps}
    mission = Mission(title=body.title, objective=body.objective, created_by_id=operator.id)
    db.add(mission)
    db.flush()
    for position, key in enumerate(order):
        step = by_key[key]
        db.add(
            WorkflowStep(
                mission_id=mission.id,
                position=position,
                **step.model_dump(),
            )
        )
    record_audit(db, "mission.created", "mission", mission.id, operator.id, {"steps": order})
    db.commit()
    return load_mission(db, mission.id)


@router.post("/missions/{mission_id}/run", response_model=MissionRead, status_code=202)
def run_mission(
    mission_id: str,
    background_tasks: BackgroundTasks,
    db: Db,
    operator: Operator,
) -> Mission:
    mission = load_mission(db, mission_id)
    if mission.status not in {MissionStatus.draft, MissionStatus.queued}:
        raise HTTPException(status_code=409, detail=f"Mission cannot run from status {mission.status.value}")
    mission.status = MissionStatus.queued
    record_audit(db, "mission.queued", "mission", mission.id, operator.id)
    db.commit()
    enqueue_mission(mission.id, background_tasks)
    return mission


@router.get("/approvals", response_model=list[ApprovalRead])
def list_approvals(
    db: Db,
    _user: CurrentUser,
    approval_status: ApprovalStatus | None = Query(default=None, alias="status"),
) -> list[Approval]:
    statement = select(Approval).order_by(desc(Approval.requested_at))
    if approval_status:
        statement = statement.where(Approval.status == approval_status)
    return list(db.scalars(statement).all())


def decide_approval(
    approval_id: str,
    decision: ApprovalStatus,
    body: ApprovalDecision,
    background_tasks: BackgroundTasks,
    db: Session,
    admin: User,
) -> Approval:
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=409, detail="Approval has already been decided")
    approval.status = decision
    approval.decided_at = utcnow()
    approval.decided_by_id = admin.id
    approval.decision_note = body.note
    step = db.get(WorkflowStep, approval.step_id)
    mission = db.get(Mission, approval.mission_id)
    assert step is not None and mission is not None
    if decision == ApprovalStatus.approved:
        step.status = StepStatus.pending
        mission.status = MissionStatus.queued
    else:
        step.status = StepStatus.rejected
        mission.status = MissionStatus.rejected
    record_audit(
        db,
        f"approval.{decision.value}",
        "approval",
        approval.id,
        admin.id,
        {"mission_id": mission.id, "step_id": step.id, "note": body.note},
    )
    db.commit()
    if decision == ApprovalStatus.approved:
        enqueue_mission(mission.id, background_tasks)
    db.refresh(approval)
    return approval


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRead)
def approve(
    approval_id: str,
    body: ApprovalDecision,
    background_tasks: BackgroundTasks,
    db: Db,
    admin: Admin,
) -> Approval:
    return decide_approval(approval_id, ApprovalStatus.approved, body, background_tasks, db, admin)


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalRead)
def reject(
    approval_id: str,
    body: ApprovalDecision,
    background_tasks: BackgroundTasks,
    db: Db,
    admin: Admin,
) -> Approval:
    return decide_approval(approval_id, ApprovalStatus.rejected, body, background_tasks, db, admin)


@router.post("/documents", response_model=DocumentRead, status_code=201)
def ingest_document(body: DocumentCreate, db: Db, operator: Operator) -> Document:
    document = Document(
        title=body.title,
        content=body.content,
        metadata_json=body.metadata,
        created_by_id=operator.id,
    )
    db.add(document)
    db.flush()
    try:
        build_memory(get_settings()).index(document)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Memory backend rejected the document") from exc
    record_audit(db, "document.ingested", "document", document.id, operator.id)
    db.commit()
    db.refresh(document)
    return document


@router.get("/documents/search", response_model=list[SearchHit])
def search_documents(
    q: str,
    db: Db,
    _user: CurrentUser,
    limit: int = Query(default=5, ge=1, le=50),
) -> list[SearchHit]:
    try:
        return build_memory(get_settings()).search(db, q, limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Memory backend is unavailable") from exc


@router.get("/audit", response_model=list[AuditRead])
def audit_history(
    db: Db,
    _admin: Admin,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditEvent]:
    return list(db.scalars(select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(limit)).all())
