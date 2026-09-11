import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .audit import record_audit
from .config import Settings
from .governance import GovernancePolicy
from .models import (
    Approval,
    ApprovalStatus,
    Handoff,
    Mission,
    MissionStatus,
    StepStatus,
    WorkflowStep,
    utcnow,
)
from .runtime import RuntimeEngine

logger = logging.getLogger(__name__)


class MissionExecutor:
    def __init__(self, settings: Settings) -> None:
        self.runtime = RuntimeEngine(settings)
        self.policy = GovernancePolicy()

    def execute(self, db: Session, mission_id: str) -> Mission:
        mission = self._load(db, mission_id)
        if mission.status in {MissionStatus.completed, MissionStatus.failed, MissionStatus.rejected}:
            return mission
        mission.status = MissionStatus.running
        record_audit(db, "mission.started", "mission", mission.id)
        db.commit()

        while True:
            mission = self._load(db, mission_id)
            if any(step.status == StepStatus.rejected for step in mission.steps):
                mission.status = MissionStatus.rejected
                record_audit(db, "mission.rejected", "mission", mission.id)
                db.commit()
                return mission
            if any(step.status == StepStatus.failed for step in mission.steps):
                mission.status = MissionStatus.failed
                record_audit(db, "mission.failed", "mission", mission.id)
                db.commit()
                return mission
            if all(step.status == StepStatus.completed for step in mission.steps):
                mission.status = MissionStatus.completed
                record_audit(db, "mission.completed", "mission", mission.id)
                db.commit()
                return mission

            completed = {step.key for step in mission.steps if step.status == StepStatus.completed}
            ready = [
                step
                for step in mission.steps
                if step.status == StepStatus.pending and set(step.depends_on) <= completed
            ]
            progressed = False
            for step in ready:
                if not self._approval_allows(db, mission, step):
                    continue
                progressed = True
                self._run_step(db, mission, step)
                if step.status == StepStatus.failed:
                    break

            if not progressed:
                mission = self._load(db, mission_id)
                if any(step.status == StepStatus.waiting_approval for step in mission.steps):
                    mission.status = MissionStatus.waiting_approval
                    db.commit()
                    return mission
                mission.status = MissionStatus.failed
                record_audit(
                    db,
                    "mission.deadlocked",
                    "mission",
                    mission.id,
                    details={"reason": "no runnable workflow steps"},
                )
                db.commit()
                return mission

    def _approval_allows(self, db: Session, mission: Mission, step: WorkflowStep) -> bool:
        gate = self.policy.evaluate(step)
        if not gate.requires_approval:
            return True
        approval = db.scalar(select(Approval).where(Approval.step_id == step.id))
        if approval is None:
            approval = Approval(
                mission_id=mission.id,
                step_id=step.id,
                reason=gate.reason,
            )
            db.add(approval)
            db.flush()
            step.status = StepStatus.waiting_approval
            record_audit(
                db,
                "approval.requested",
                "approval",
                approval.id,
                details={"mission_id": mission.id, "step_id": step.id, "reason": gate.reason},
            )
            db.commit()
            return False
        if approval.status == ApprovalStatus.approved:
            return True
        if approval.status == ApprovalStatus.rejected:
            step.status = StepStatus.rejected
            db.commit()
            return False
        step.status = StepStatus.waiting_approval
        db.commit()
        return False

    def _run_step(self, db: Session, mission: Mission, step: WorkflowStep) -> None:
        dependencies = {candidate.key: candidate for candidate in mission.steps}
        context = {
            key: dependencies[key].output or ""
            for key in step.depends_on
        }
        for source_key in step.depends_on:
            source = dependencies[source_key]
            db.add(
                Handoff(
                    mission_id=mission.id,
                    from_step_id=source.id,
                    to_step_id=step.id,
                    payload={"output": source.output or ""},
                )
            )
        step.status = StepStatus.running
        step.started_at = utcnow()
        record_audit(db, "step.started", "workflow_step", step.id)
        db.commit()
        try:
            step.output = self.runtime.run(step, context)
            step.status = StepStatus.completed
            step.completed_at = utcnow()
            record_audit(db, "step.completed", "workflow_step", step.id)
        except Exception as exc:  # provider/network failures become persisted mission failures
            logger.exception("Step execution failed", extra={"mission_id": mission.id})
            step.status = StepStatus.failed
            step.error = f"{type(exc).__name__}: {exc}"
            step.completed_at = utcnow()
            record_audit(
                db,
                "step.failed",
                "workflow_step",
                step.id,
                details={"error_type": type(exc).__name__},
            )
        db.commit()

    @staticmethod
    def _load(db: Session, mission_id: str) -> Mission:
        mission = db.scalar(
            select(Mission)
            .where(Mission.id == mission_id)
            .options(selectinload(Mission.steps).selectinload(WorkflowStep.agent))
        )
        if mission is None:
            raise LookupError(f"Mission {mission_id} not found")
        return mission
