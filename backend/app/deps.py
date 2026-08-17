from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from .database import get_db
from .config import get_settings
from .models import User, UserSession
from .security import hash_session_token
from .services.menus import has_menu_permission


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    session = db.query(UserSession).filter(UserSession.token_hash == hash_session_token(token)).first()
    now = datetime.now()
    settings = get_settings()
    if not session or session.revoked_date or session.expire_date <= now or session.last_active_date + timedelta(minutes=settings.session_idle_timeout_minutes) <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    if request.headers.get("X-Session-Activity") == "1":
        session.last_active_date = now
        db.commit()
    user = db.get(User, session.user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")
    allowed_paths = {"/auth/me", "/auth/logout", "/auth/change-password"}
    path = request.url.path.removeprefix("/api")
    if path not in allowed_paths and not has_menu_permission(db, user.role, path):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色无权访问该功能")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可以创建账号")
    return user

