import json
import logging

from .config import get_settings
from .database import SessionLocal
from .kernel import Kernel
from .logging import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.execution_backend != "redis":
        raise SystemExit("Worker requires RX_EXECUTION_BACKEND=redis")
    try:
        import redis
    except ImportError as exc:
        raise SystemExit("Install the 'redis' extra to run the worker") from exc
    client = redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("Worker ready")
    while True:
        item = client.blpop("rx_ai_omega:missions", timeout=5)
        if item is None:
            continue
        _, raw = item
        try:
            mission_id = json.loads(raw)["mission_id"]
            with SessionLocal() as db:
                Kernel(settings).execute(db, mission_id)
        except Exception:
            logger.exception("Worker job failed")


if __name__ == "__main__":
    main()
