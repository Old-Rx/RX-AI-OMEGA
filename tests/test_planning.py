import pytest

from rx_ai_omega.planning import InvalidPlan, validate_and_order
from rx_ai_omega.schemas import StepCreate


def step(key: str, depends_on: list[str] | None = None) -> StepCreate:
    return StepCreate(key=key, agent_id="agent", prompt="work", depends_on=depends_on or [])


def test_plan_is_topologically_ordered() -> None:
    ordered = validate_and_order([step("ship", ["test"]), step("test", ["build"]), step("build")])
    assert ordered == ["build", "test", "ship"]


@pytest.mark.parametrize(
    "steps, message",
    [
        ([step("a"), step("a")], "unique"),
        ([step("a", ["missing"])], "unknown"),
        ([step("a", ["b"]), step("b", ["a"])], "cycle"),
        ([step("a", ["a"])], "itself"),
    ],
)
def test_invalid_plans_are_rejected(steps: list[StepCreate], message: str) -> None:
    with pytest.raises(InvalidPlan, match=message):
        validate_and_order(steps)
