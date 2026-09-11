from dataclasses import dataclass

from .models import WorkflowStep


@dataclass(frozen=True)
class GateDecision:
    requires_approval: bool
    reason: str


class GovernancePolicy:
    controlled_actions = {"production", "release", "deploy", "delete", "publish"}

    def evaluate(self, step: WorkflowStep) -> GateDecision:
        risky_action = step.action.lower() in self.controlled_actions
        requires = step.risk in {"medium", "high"} or risky_action
        reasons: list[str] = []
        if step.risk in {"medium", "high"}:
            reasons.append(f"{step.risk}-risk step")
        if risky_action:
            reasons.append(f"controlled '{step.action}' action")
        return GateDecision(requires, " and ".join(reasons) or "no approval required")
