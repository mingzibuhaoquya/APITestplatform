from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..models import User
from ..schemas import ChangePasswordIn, LoginIn, UserOut
from ..security import create_session_token, hash_password, verify_password
from ..utils import fmt_time


router = APIRouter(prefix="/auth", tags=["auth"])


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        role=user.role,
        status=user.status,
        create_date=fmt_time(user.create_date),
        update_date=fmt_time(user.update_date),
    )


@router.post("/login")
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=400, detail="账号不可用")
    user.last_login_time = datetime.now()
    db.commit()
    token = create_session_token(user.id)
    response.set_cookie("session", token, httponly=True, samesite="lax")
    return {"token": token, "user": user_out(user)}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}


@router.post("/change-password")
def change_password(payload: ChangePasswordIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码一致")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)
