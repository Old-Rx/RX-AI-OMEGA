from collections import deque

from .schemas import StepCreate


class InvalidPlan(ValueError):
    pass


def validate_and_order(steps: list[StepCreate]) -> list[str]:
    keys = [step.key for step in steps]
    if len(keys) != len(set(keys)):
        raise InvalidPlan("step keys must be unique")
    known = set(keys)
    indegree = {key: 0 for key in keys}
    dependents: dict[str, list[str]] = {key: [] for key in keys}
    for step in steps:
        if step.key in step.depends_on:
            raise InvalidPlan(f"step '{step.key}' cannot depend on itself")
        missing = set(step.depends_on) - known
        if missing:
            raise InvalidPlan(f"step '{step.key}' has unknown dependencies: {sorted(missing)}")
        if len(step.depends_on) != len(set(step.depends_on)):
            raise InvalidPlan(f"step '{step.key}' contains duplicate dependencies")
        indegree[step.key] = len(step.depends_on)
        for dependency in step.depends_on:
            dependents[dependency].append(step.key)
    ready = deque(key for key in keys if indegree[key] == 0)
    ordered: list[str] = []
    while ready:
        key = ready.popleft()
        ordered.append(key)
        for dependent in dependents[key]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if len(ordered) != len(keys):
        raise InvalidPlan("workflow contains a dependency cycle")
    return ordered
