from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import admin_user
from ..models import User
from ..schemas import UserCreate
from ..security import hash_password
from .auth import user_out


router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [user_out(user) for user in db.query(User).order_by(User.id.desc()).all()]


@router.post("")
def create_user(payload: UserCreate, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        real_name=payload.real_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_out(user)

