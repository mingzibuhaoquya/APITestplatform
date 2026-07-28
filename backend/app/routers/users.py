from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import admin_user, current_user
from ..models import User
from ..schemas import UserCreate, UserListOut, UserStatusUpdate, UserUpdate
from ..security import hash_password
from .auth import user_out


router = APIRouter(prefix="/users", tags=["users"])


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
        "items": [user_out(user) for user in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("")
def create_user(payload: UserCreate, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    username = payload.username.strip()
    real_name = payload.real_name.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    if not real_name:
        raise HTTPException(status_code=400, detail="real_name is required")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        real_name=real_name,
        role=payload.role,
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, _: User = Depends(current_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    username = payload.username.strip()
    real_name = payload.real_name.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    if not real_name:
        raise HTTPException(status_code=400, detail="real_name is required")
    exists = db.query(User).filter(User.username == username, User.id != user_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user.username = username
    user.real_name = real_name
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.patch("/{user_id}/status")
def update_user_status(user_id: int, payload: UserStatusUpdate, _: User = Depends(current_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = payload.status
    db.commit()
    db.refresh(user)
    return user_out(user)
