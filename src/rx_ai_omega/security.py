from datetime import UTC, datetime, timedelta
from collections.abc import Callable
from typing import Annotated, TypeAlias

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import Role, User

password_hasher = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.auth_secret, algorithm="HS256")


def current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, get_settings().auth_secret, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            raise credentials_error
    except InvalidTokenError as exc:
        raise credentials_error from exc
    user = db.get(User, user_id)
    if user is None or not user.active:
        raise credentials_error
    return user


CurrentUser: TypeAlias = Annotated[User, Depends(current_user)]


def require_role(*allowed: Role) -> Callable[[User], User]:
    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency


Operator: TypeAlias = Annotated[User, Depends(require_role(Role.operator, Role.admin))]
Admin: TypeAlias = Annotated[User, Depends(require_role(Role.admin))]
