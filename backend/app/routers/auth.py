from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..models import Role, User, UserSession
from ..schemas import ChangePasswordIn, LoginIn, UserOut
from ..config import get_settings
from ..security import create_user_session, hash_password, hash_session_token, revoke_user_sessions, verify_password
from ..services.menus import role_menus
from ..services.operation_logs import log_operation
from ..utils import fmt_time


router = APIRouter(prefix="/auth", tags=["auth"])


def user_out(user: User, db: Session) -> UserOut:
    role = db.query(Role).filter(Role.code == user.role).first()
    role_name = role.name if role else user.role
    menus = role_menus(role, user.role)
    return UserOut(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        role=user.role,
        role_name=role_name,
        menus=menus,
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
    token = create_user_session(db, user.id)
    db.commit()
    log_operation(db, user, "auth", "login", f"user {user.username} logged in")
    settings = get_settings()
    response.set_cookie(
        "session", token, httponly=True, samesite="lax", secure=settings.session_cookie_secure, path="/",
        max_age=settings.session_absolute_timeout_hours * 3600,
    )
    return {"user": user_out(user, db)}


@router.post("/logout")
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    log_operation(db, user, "auth", "logout", f"user {user.username} logged out")
    token = request.cookies.get("session", "")
    session = db.query(UserSession).filter(UserSession.token_hash == hash_session_token(token)).first()
    if session and session.revoked_date is None:
        session.revoked_date = datetime.now()
        db.commit()
    response.delete_cookie("session", path="/")
    return {"ok": True}


@router.post("/change-password")
def change_password(payload: ChangePasswordIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码一致")
    user.password_hash = hash_password(payload.new_password)
    revoke_user_sessions(db, user.id)
    db.commit()
    log_operation(db, user, "auth", "change_password", f"user {user.username} changed password")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_out(user, db)
