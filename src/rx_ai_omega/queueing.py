import json
import logging
from collections.abc import Callable

from fastapi import BackgroundTasks

from .config import Settings

logger = logging.getLogger(__name__)


class MissionQueue:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def enqueue(
        self,
        mission_id: str,
        background_tasks: BackgroundTasks,
        local_runner: Callable[[str], None],
    ) -> None:
        if self.settings.execution_backend == "local":
            background_tasks.add_task(local_runner, mission_id)
            return
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("Install the 'redis' extra for Redis execution") from exc
        client = redis.from_url(self.settings.redis_url, decode_responses=True)
        client.rpush("rx_ai_omega:missions", json.dumps({"mission_id": mission_id}))
