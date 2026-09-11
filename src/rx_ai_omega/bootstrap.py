import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .models import Role, User
from .security import hash_password

logger = logging.getLogger(__name__)


def bootstrap_admin(db: Session, settings: Settings) -> None:
    if not settings.bootstrap_admin_username or not settings.bootstrap_admin_password:
        return
    if db.scalar(select(User.id).limit(1)) is not None:
        return
    user = User(
        username=settings.bootstrap_admin_username,
        password_hash=hash_password(settings.bootstrap_admin_password),
        role=Role.admin,
    )
    db.add(user)
    db.commit()
    logger.warning(
        "Bootstrap administrator created; rotate or disable bootstrap credentials",
        extra={"user_id": user.id},
    )
