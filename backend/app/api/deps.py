from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)
LOCAL_GUEST_EMAIL = "local-guest@star.local"
LOCAL_GUEST_PASSWORD_HASH = "local-guest-no-login"
LOCAL_GUEST_DISPLAY_NAME = "本地游客"


def get_or_create_local_guest(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == LOCAL_GUEST_EMAIL))
    if user is not None:
        return user

    user = User(
        email=LOCAL_GUEST_EMAIL,
        password_hash=LOCAL_GUEST_PASSWORD_HASH,
        display_name=LOCAL_GUEST_DISPLAY_NAME,
        plan_type="local_guest",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        return get_or_create_local_guest(db)

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        return get_or_create_local_guest(db)

    user_id = payload.get("sub")
    if not user_id:
        return get_or_create_local_guest(db)

    user = db.scalar(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    if user is None:
        return get_or_create_local_guest(db)
    return user
