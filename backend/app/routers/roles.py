from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Role, User
from ..schemas import RoleIn, RoleListOut, RoleUpdate
from ..services.menus import MENU_TREE, ensure_default_roles, normalize_menus, role_menus
from ..services.operation_logs import log_operation
from ..utils import dump_json, fmt_time, parse_json


router = APIRouter(prefix="/roles", tags=["roles"])


def _role_out(row: Role, db: Session):
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "description": row.description,
        "status": row.status,
        "is_builtin": row.is_builtin,
        "menus": normalize_menus(parse_json(row.menus_json, [])),
        "user_count": db.query(User).filter(User.role == row.code).count(),
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


def _require_role_code_available(db: Session, code: str, role_id: int | None = None) -> None:
    exists = db.query(Role).filter(Role.code == code).first()
    if exists and exists.id != role_id:
        raise HTTPException(status_code=400, detail="角色编码已存在")


def _require_role_menu(operator: User, db: Session) -> None:
    if operator.role == "admin":
        return
    role = db.query(Role).filter(Role.code == operator.role).first()
    if "roles" not in role_menus(role, operator.role):
        raise HTTPException(status_code=403, detail="当前角色无权维护角色")


@router.get("/menus")
def list_role_menus(_: User = Depends(current_user)):
    return MENU_TREE


@router.get("", response_model=RoleListOut)
def list_roles(
    name: str = "",
    status: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=20),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    ensure_default_roles(db)
    query = db.query(Role)
    if name.strip():
        query = query.filter(Role.name.like(f"%{name.strip()}%"))
    if status.strip():
        query = query.filter(Role.status == status.strip())
    total = query.count()
    rows = query.order_by(Role.is_builtin.desc(), Role.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_role_out(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("")
def create_role(payload: RoleIn, operator: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_role_menu(operator, db)
    code = payload.code.strip()
    name = payload.name.strip()
    if not code:
        raise HTTPException(status_code=400, detail="角色编码不能为空")
    if not code.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="角色编码只能包含字母、数字、中划线或下划线")
    if not name:
        raise HTTPException(status_code=400, detail="角色名称不能为空")
    _require_role_code_available(db, code)
    row = Role(
        code=code,
        name=name,
        description=payload.description.strip(),
        status=payload.status,
        is_builtin=False,
        menus_json=dump_json(normalize_menus(payload.menus)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_operation(db, operator, "role", "create", f"created role {row.code}")
    return _role_out(row, db)


@router.put("/{role_id}")
def update_role(role_id: int, payload: RoleUpdate, operator: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_role_menu(operator, db)
    row = db.get(Role, role_id)
    if not row:
        raise HTTPException(status_code=404, detail="角色不存在")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="角色名称不能为空")
    row.name = name
    row.description = payload.description.strip()
    row.status = payload.status
    row.menus_json = dump_json(normalize_menus(payload.menus))
    db.commit()
    db.refresh(row)
    log_operation(db, operator, "role", "update", f"updated role {row.code}")
    return _role_out(row, db)


@router.delete("/{role_id}")
def delete_role(role_id: int, operator: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_role_menu(operator, db)
    row = db.get(Role, role_id)
    if not row:
        raise HTTPException(status_code=404, detail="角色不存在")
    if row.is_builtin:
        raise HTTPException(status_code=400, detail="内置角色不能删除")
    if db.query(User).filter(User.role == row.code).count() > 0:
        raise HTTPException(status_code=400, detail="该角色已绑定用户，请先调整用户角色")
    data = _role_out(row, db)
    db.delete(row)
    db.commit()
    log_operation(db, operator, "role", "delete", f"deleted role {data['code']}")
    return data
