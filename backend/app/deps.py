from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .security import read_session_token
from .services.menus import has_menu_permission


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("session")
    if not token:
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
    user_id = read_session_token(token) if token else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    user = db.get(User, user_id)
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

