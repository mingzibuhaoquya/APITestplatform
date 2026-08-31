from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import KnowledgeBase, KnowledgeProject, User
from ..schemas import KnowledgeProjectIn, KnowledgeProjectUpdate
from ..services.operation_logs import log_operation
from ..utils import fmt_time


router = APIRouter(prefix="/knowledge-projects", tags=["knowledge-projects"])


def _out(row: KnowledgeProject, db: Session) -> dict:
    creator = db.get(User, row.creator_id) if row.creator_id else None
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "status": row.status,
        "creator_name": creator.real_name or creator.username if creator else "",
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


def _require_name_available(db: Session, name: str, project_id: int | None = None) -> None:
    exists = db.query(KnowledgeProject).filter(
        KnowledgeProject.name == name,
        KnowledgeProject.is_deleted.is_(False),
    ).first()
    if exists and exists.id != project_id:
        raise HTTPException(status_code=400, detail="知识库项目名称已存在")


@router.get("")
def list_knowledge_projects(
    name: str = "",
    status: str = "",
    page: int | None = None,
    page_size: int | None = None,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(KnowledgeProject).filter(KnowledgeProject.is_deleted.is_(False))
    if name.strip():
        query = query.filter(KnowledgeProject.name.like(f"%{name.strip()}%"))
    if status.strip():
        query = query.filter(KnowledgeProject.status == status.strip())
    if page is None and page_size is None:
        return [_out(row, db) for row in query.order_by(KnowledgeProject.id.desc()).all()]
    page = max(page or 1, 1)
    page_size = min(max(page_size or 10, 1), 20)
    total = query.count()
    rows = query.order_by(KnowledgeProject.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_out(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201)
def create_knowledge_project(payload: KnowledgeProjectIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="知识库项目名称不能为空")
    _require_name_available(db, name)
    row = KnowledgeProject(name=name, description=payload.description.strip(), status=payload.status, creator_id=user.id, is_deleted=False)
    db.add(row)
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_project", "create", f"created knowledge project {row.name}")
    return _out(row, db)


@router.put("/{project_id}")
def update_knowledge_project(project_id: int, payload: KnowledgeProjectUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(KnowledgeProject, project_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="知识库项目不存在")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="知识库项目名称不能为空")
    _require_name_available(db, name, row.id)
    row.name = name
    row.description = payload.description.strip()
    row.status = payload.status
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_project", "update", f"updated knowledge project {row.name}")
    return _out(row, db)


@router.delete("/{project_id}")
def delete_knowledge_project(project_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(KnowledgeProject, project_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="知识库项目不存在")
    if db.query(KnowledgeBase).filter(KnowledgeBase.project_id == row.id, KnowledgeBase.is_deleted.is_(False)).first():
        raise HTTPException(status_code=400, detail="该项目下存在知识库绑定，请先删除绑定")
    row.is_deleted = True
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_project", "delete", f"deleted knowledge project {row.name}")
    return _out(row, db)
