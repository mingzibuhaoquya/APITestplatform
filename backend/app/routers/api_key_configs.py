import os
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import ApiKeyConfig, User
from ..schemas import ApiKeyConfigIn, ApiKeyConfigUpdate
from ..services.operation_logs import log_operation
from ..utils import fmt_time


router = APIRouter(prefix="/api-key-configs", tags=["api-key-configs"])

ENV_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _normalize_env_key(value: str) -> str:
    env_key = value.strip()
    if not env_key:
        raise HTTPException(status_code=400, detail="环境变量名不能为空")
    if not ENV_KEY_PATTERN.fullmatch(env_key):
        raise HTTPException(status_code=400, detail="环境变量名只允许大写字母、数字、下划线，且必须以大写字母开头")
    return env_key


def _active_row(db: Session, row_id: int) -> ApiKeyConfig:
    row = db.get(ApiKeyConfig, row_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="API Key配置不存在")
    return row


def _require_unique_env_key(db: Session, env_key: str, row_id: int | None = None) -> None:
    exists = db.query(ApiKeyConfig).filter(ApiKeyConfig.env_key == env_key, ApiKeyConfig.is_deleted.is_(False)).first()
    if exists and exists.id != row_id:
        raise HTTPException(status_code=400, detail="环境变量名已存在")


def _out(row: ApiKeyConfig, db: Session) -> dict:
    creator = db.get(User, row.creator_id) if row.creator_id else None
    return {
        "id": row.id,
        "env_key": row.env_key,
        "display_name": row.display_name,
        "configured": bool(os.getenv(row.env_key, "").strip()),
        "status": row.status,
        "description": row.description,
        "creator_name": creator.real_name or creator.username if creator else "",
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


def require_api_key_config(db: Session, env_key: str) -> ApiKeyConfig:
    normalized = _normalize_env_key(env_key)
    row = db.query(ApiKeyConfig).filter(
        ApiKeyConfig.env_key == normalized,
        ApiKeyConfig.is_deleted.is_(False),
        ApiKeyConfig.status == "active",
    ).first()
    if not row:
        raise HTTPException(status_code=400, detail="API Key环境变量未在系统管理中配置或已禁用")
    return row


@router.get("")
def list_api_key_configs(
    keyword: str = "",
    status: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ApiKeyConfig).filter(ApiKeyConfig.is_deleted.is_(False))
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        query = query.filter((ApiKeyConfig.env_key.like(like)) | (ApiKeyConfig.display_name.like(like)))
    if status.strip():
        query = query.filter(ApiKeyConfig.status == status.strip())
    total = query.count()
    rows = query.order_by(ApiKeyConfig.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_out(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/options")
def list_api_key_config_options(
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(ApiKeyConfig).filter(ApiKeyConfig.is_deleted.is_(False), ApiKeyConfig.status == "active").order_by(ApiKeyConfig.id.asc()).all()
    return [_out(row, db) for row in rows]


@router.post("", status_code=201)
def create_api_key_config(payload: ApiKeyConfigIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    env_key = _normalize_env_key(payload.env_key)
    display_name = payload.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="中文名不能为空")
    _require_unique_env_key(db, env_key)
    row = ApiKeyConfig(
        env_key=env_key,
        display_name=display_name,
        status=payload.status,
        description=payload.description.strip(),
        creator_id=user.id,
        is_deleted=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_operation(db, user, "api_key_config", "create", f"created api key config {row.env_key}")
    return _out(row, db)


@router.put("/{config_id}")
def update_api_key_config(config_id: int, payload: ApiKeyConfigUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _active_row(db, config_id)
    env_key = _normalize_env_key(payload.env_key)
    display_name = payload.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="中文名不能为空")
    _require_unique_env_key(db, env_key, row.id)
    row.env_key = env_key
    row.display_name = display_name
    row.status = payload.status
    row.description = payload.description.strip()
    db.commit()
    db.refresh(row)
    log_operation(db, user, "api_key_config", "update", f"updated api key config {row.env_key}")
    return _out(row, db)


@router.delete("/{config_id}")
def delete_api_key_config(config_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _active_row(db, config_id)
    row.is_deleted = True
    db.commit()
    db.refresh(row)
    log_operation(db, user, "api_key_config", "delete", f"deleted api key config {row.env_key}")
    return _out(row, db)
