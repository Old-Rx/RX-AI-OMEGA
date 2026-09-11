from typing import Any

from sqlalchemy.orm import Session

from .models import AuditEvent


def record_audit(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: str,
    actor_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )
    db.add(event)
    return event
