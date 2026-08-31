from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import KnowledgeBase, KnowledgeProject, KnowledgeQueryLog, User
from ..schemas import KnowledgeBaseIn, KnowledgeBaseUpdate, KnowledgeCheckIn, KnowledgeRetrieveIn
from ..services.dify_knowledge import DifyKnowledgeError, check_dataset, list_datasets, list_documents, retrieve
from ..services.operation_logs import log_operation
from ..utils import fmt_time


router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


def _project(db: Session, project_id: int, require_enabled: bool = False) -> KnowledgeProject:
    row = db.get(KnowledgeProject, project_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=400, detail="知识库项目不存在")
    if require_enabled and row.status != "active":
        raise HTTPException(status_code=400, detail="知识库项目已禁用")
    return row


def _require_available(db: Session, project_id: int, name: str, dataset_id: str, row_id: int | None = None) -> None:
    exists_name = db.query(KnowledgeBase).filter(
        KnowledgeBase.project_id == project_id,
        KnowledgeBase.name == name,
        KnowledgeBase.is_deleted.is_(False),
    ).first()
    if exists_name and exists_name.id != row_id:
        raise HTTPException(status_code=400, detail="同一项目下知识库名称已存在")
    exists_dataset = db.query(KnowledgeBase).filter(
        KnowledgeBase.project_id == project_id,
        KnowledgeBase.dify_dataset_id == dataset_id,
        KnowledgeBase.is_deleted.is_(False),
    ).first()
    if exists_dataset and exists_dataset.id != row_id:
        raise HTTPException(status_code=400, detail="同一项目下 Dify 知识库已绑定")


def _out(row: KnowledgeBase, db: Session) -> dict:
    project = db.get(KnowledgeProject, row.project_id)
    creator = db.get(User, row.creator_id) if row.creator_id else None
    return {
        "id": row.id,
        "project_id": row.project_id,
        "project_name": project.name if project and not project.is_deleted else "",
        "name": row.name,
        "dify_dataset_id": row.dify_dataset_id,
        "status": row.status,
        "description": row.description,
        "creator_name": creator.real_name or creator.username if creator else "",
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


def _active_row(db: Session, row_id: int, require_enabled: bool = False) -> KnowledgeBase:
    row = db.get(KnowledgeBase, row_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="知识库绑定不存在")
    if require_enabled and row.status != "active":
        raise HTTPException(status_code=400, detail="知识库绑定已禁用")
    _project(db, row.project_id, require_enabled=require_enabled)
    return row


@router.get("")
def list_knowledge_bases(
    project_id: int | None = None,
    name: str = "",
    status: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=20),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(KnowledgeBase).join(KnowledgeProject, KnowledgeBase.project_id == KnowledgeProject.id).filter(
        KnowledgeBase.is_deleted.is_(False),
        KnowledgeProject.is_deleted.is_(False),
    )
    if project_id:
        query = query.filter(KnowledgeBase.project_id == project_id)
    if name.strip():
        query = query.filter(KnowledgeBase.name.like(f"%{name.strip()}%"))
    if status.strip():
        query = query.filter(KnowledgeBase.status == status.strip())
    total = query.count()
    rows = query.order_by(KnowledgeBase.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_out(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201)
def create_knowledge_base(payload: KnowledgeBaseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _project(db, payload.project_id, require_enabled=True)
    name = payload.name.strip()
    dataset_id = payload.dify_dataset_id.strip()
    if not name:
        raise HTTPException(status_code=400, detail="知识库名称不能为空")
    if not dataset_id:
        raise HTTPException(status_code=400, detail="Dify Dataset ID 不能为空")
    _require_available(db, payload.project_id, name, dataset_id)
    row = KnowledgeBase(
        project_id=payload.project_id,
        name=name,
        dify_dataset_id=dataset_id,
        status=payload.status,
        description=payload.description.strip(),
        creator_id=user.id,
        is_deleted=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_base", "create", f"created knowledge base {row.name}")
    return _out(row, db)


@router.post("/check")
def check_knowledge_dataset(payload: KnowledgeCheckIn, _: User = Depends(current_user)):
    dataset_id = payload.dify_dataset_id.strip()
    if not dataset_id:
        raise HTTPException(status_code=400, detail="Dify Dataset ID 不能为空")
    try:
        return check_dataset(dataset_id)
    except DifyKnowledgeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/dify-datasets")
def list_dify_datasets(
    keyword: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    _: User = Depends(current_user),
):
    try:
        return list_datasets(keyword, page, page_size)
    except DifyKnowledgeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.put("/{knowledge_base_id}")
def update_knowledge_base(knowledge_base_id: int, payload: KnowledgeBaseUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _active_row(db, knowledge_base_id)
    _project(db, payload.project_id, require_enabled=True)
    name = payload.name.strip()
    dataset_id = payload.dify_dataset_id.strip()
    if not name:
        raise HTTPException(status_code=400, detail="知识库名称不能为空")
    if not dataset_id:
        raise HTTPException(status_code=400, detail="Dify Dataset ID 不能为空")
    _require_available(db, payload.project_id, name, dataset_id, row.id)
    row.project_id = payload.project_id
    row.name = name
    row.dify_dataset_id = dataset_id
    row.status = payload.status
    row.description = payload.description.strip()
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_base", "update", f"updated knowledge base {row.name}")
    return _out(row, db)


@router.delete("/{knowledge_base_id}")
def delete_knowledge_base(knowledge_base_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _active_row(db, knowledge_base_id)
    row.is_deleted = True
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_base", "delete", f"deleted knowledge base {row.name}")
    return _out(row, db)


@router.post("/{knowledge_base_id}/check")
def check_knowledge_base(knowledge_base_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _active_row(db, knowledge_base_id)
    try:
        return check_dataset(row.dify_dataset_id)
    except DifyKnowledgeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{knowledge_base_id}/documents")
def get_documents(
    knowledge_base_id: int,
    keyword: str = "",
    status: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=20),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = _active_row(db, knowledge_base_id, require_enabled=True)
    try:
        return list_documents(row.dify_dataset_id, keyword, status, page, page_size)
    except DifyKnowledgeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{knowledge_base_id}/retrieve")
def retrieve_knowledge_base(knowledge_base_id: int, payload: KnowledgeRetrieveIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _active_row(db, knowledge_base_id, require_enabled=True)
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="请输入检索内容")
    log = KnowledgeQueryLog(
        knowledge_base_id=row.id,
        project_id=row.project_id,
        query_text=query,
        operator_id=user.id,
    )
    db.add(log)
    db.commit()
    try:
        result, duration_ms = retrieve(row.dify_dataset_id, query, payload.top_k, payload.score_threshold)
        hits = result.get("hits") if isinstance(result.get("hits"), list) else []
        log.hit_count = len(hits)
        log.duration_ms = duration_ms
        db.commit()
        return {**result, "duration_ms": duration_ms}
    except DifyKnowledgeError as exc:
        log.error_message = str(exc)[:4000]
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
