from sqlalchemy.orm import Session

from .config import Settings
from .executor import MissionExecutor
from .models import Mission


class Kernel:
    """Stable orchestration boundary retained from the verified v32 design lineage."""

    def __init__(self, settings: Settings) -> None:
        self.executor = MissionExecutor(settings)

    def execute(self, db: Session, mission_id: str) -> Mission:
        return self.executor.execute(db, mission_id)
