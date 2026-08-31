from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import admin_user, current_user
from ..models import Role, User
from ..schemas import UserCreate, UserListOut, UserStatusUpdate, UserUpdate
from ..security import hash_password, revoke_user_sessions
from ..services.menus import ensure_default_roles
from ..services.operation_logs import log_operation
from .auth import user_out


router = APIRouter(prefix="/users", tags=["users"])


def _active_role(db: Session, code: str) -> Role:
    ensure_default_roles(db)
    role = db.query(Role).filter(Role.code == code).first()
    if not role or role.status != "active":
        raise HTTPException(status_code=400, detail="角色不存在或已禁用")
    return role


@router.get("", response_model=UserListOut)
def list_users(
    username: str = "",
    status: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=10),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 10)
    query = db.query(User)
    if username.strip():
        query = query.filter(User.username.like(f"%{username.strip()}%"))
    if status.strip():
        query = query.filter(User.status == status.strip())
    total = query.count()
    rows = (
        query
        .order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [user_out(user, db) for user in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("")
def create_user(payload: UserCreate, operator: User = Depends(admin_user), db: Session = Depends(get_db)):
    username = payload.username.strip()
    real_name = payload.real_name.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    if not real_name:
        raise HTTPException(status_code=400, detail="real_name is required")
    role_code = payload.role.strip()
    _active_role(db, role_code)
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        real_name=real_name,
        role=role_code,
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_operation(db, operator, "user", "create", f"created user {user.username}")
    return user_out(user, db)


@router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, operator: User = Depends(current_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    username = payload.username.strip()
    real_name = payload.real_name.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    if not real_name:
        raise HTTPException(status_code=400, detail="real_name is required")
    role_code = payload.role.strip()
    _active_role(db, role_code)
    exists = db.query(User).filter(User.username == username, User.id != user_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user.username = username
    user.real_name = real_name
    user.role = role_code
    db.commit()
    db.refresh(user)
    log_operation(db, operator, "user", "update", f"updated user {user.username}")
    return user_out(user, db)


@router.patch("/{user_id}/status")
def update_user_status(user_id: int, payload: UserStatusUpdate, operator: User = Depends(current_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = payload.status
    if user.status == "disabled":
        revoke_user_sessions(db, user.id)
    db.commit()
    db.refresh(user)
    log_operation(db, operator, "user", "status", f"updated user {user.username} status to {user.status}")
    return user_out(user, db)
