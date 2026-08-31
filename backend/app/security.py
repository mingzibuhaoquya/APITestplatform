import hashlib
import secrets
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .config import get_settings
from .models import UserSession


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_user_session(db: Session, user_id: int, now: datetime | None = None) -> str:
    now = now or datetime.now()
    settings = get_settings()
    token = secrets.token_urlsafe(48)
    db.add(UserSession(
        session_id=secrets.token_urlsafe(32),
        token_hash=hash_session_token(token),
        user_id=user_id,
        expire_date=now + timedelta(hours=settings.session_absolute_timeout_hours),
        last_active_date=now,
    ))
    return token


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def revoke_user_sessions(db: Session, user_id: int, now: datetime | None = None) -> None:
    now = now or datetime.now()
    db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.revoked_date.is_(None),
    ).update({UserSession.revoked_date: now, UserSession.update_date: now}, synchronize_session=False)
