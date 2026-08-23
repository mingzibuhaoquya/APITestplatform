import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import current_user
from ..models import KnowledgeProject, KnowledgeWorkflow, User
from ..schemas import KnowledgeWorkflowIn, KnowledgeWorkflowUpdate
from .api_key_configs import require_api_key_config
from ..services.dify_workflow_qa import DifyWorkflowQaError, run_workflow
from ..services.operation_logs import log_operation
from ..utils import fmt_time


router = APIRouter(prefix="/knowledge-workflows", tags=["knowledge-workflows"])


def _project(db: Session, project_id: int, require_enabled: bool = False) -> KnowledgeProject:
    row = db.get(KnowledgeProject, project_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=400, detail="知识库项目不存在")
    if require_enabled and row.status != "active":
        raise HTTPException(status_code=400, detail="知识库项目已禁用")
    return row


def _active_row(db: Session, row_id: int, require_enabled: bool = False) -> KnowledgeWorkflow:
    row = db.get(KnowledgeWorkflow, row_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="工作流配置不存在")
    if require_enabled and row.status != "active":
        raise HTTPException(status_code=400, detail="工作流配置已禁用")
    _project(db, row.project_id, require_enabled=require_enabled)
    return row


def _api_key_from_env(row: KnowledgeWorkflow) -> str:
    env_name = row.api_key_env.strip()
    if not env_name:
        raise HTTPException(status_code=400, detail="工作流未配置 API Key 环境变量名")
    api_key = os.getenv(env_name, "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail=f"环境变量 {env_name} 未配置或为空")
    return api_key


def _require_available(db: Session, project_id: int, name: str, row_id: int | None = None) -> None:
    exists = db.query(KnowledgeWorkflow).filter(
        KnowledgeWorkflow.project_id == project_id,
        KnowledgeWorkflow.name == name,
        KnowledgeWorkflow.is_deleted.is_(False),
    ).first()
    if exists and exists.id != row_id:
        raise HTTPException(status_code=400, detail="同一项目下工作流名称已存在")


def _out(row: KnowledgeWorkflow, db: Session) -> dict:
    project = db.get(KnowledgeProject, row.project_id)
    creator = db.get(User, row.creator_id) if row.creator_id else None
    return {
        "id": row.id,
        "project_id": row.project_id,
        "project_name": project.name if project and not project.is_deleted else "",
        "name": row.name,
        "api_base_url": row.api_base_url,
        "api_key_env": row.api_key_env,
        "status": row.status,
        "description": row.description,
        "creator_name": creator.real_name or creator.username if creator else "",
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


@router.get("")
def list_knowledge_workflows(
    project_id: int | None = None,
    name: str = "",
    status: str = "",
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(KnowledgeWorkflow).join(KnowledgeProject, KnowledgeWorkflow.project_id == KnowledgeProject.id).filter(
        KnowledgeWorkflow.is_deleted.is_(False),
        KnowledgeProject.is_deleted.is_(False),
    )
    if project_id:
        query = query.filter(KnowledgeWorkflow.project_id == project_id)
    if name.strip():
        query = query.filter(KnowledgeWorkflow.name.like(f"%{name.strip()}%"))
    if status.strip():
        query = query.filter(KnowledgeWorkflow.status == status.strip())
    query = query.order_by(KnowledgeWorkflow.id.desc())
    if page is None:
        return [_out(row, db) for row in query.all()]
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_out(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201)
def create_knowledge_workflow(payload: KnowledgeWorkflowIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _project(db, payload.project_id, require_enabled=True)
    name = payload.name.strip()
    api_key_env = payload.api_key_env.strip()
    if not name:
        raise HTTPException(status_code=400, detail="工作流名称不能为空")
    if not api_key_env:
        raise HTTPException(status_code=400, detail="API Key 环境变量名不能为空")
    require_api_key_config(db, api_key_env)
    _require_available(db, payload.project_id, name)
    row = KnowledgeWorkflow(
        project_id=payload.project_id,
        name=name,
        api_base_url=payload.api_base_url.strip(),
        api_key="",
        api_key_env=api_key_env,
        status=payload.status,
        description=payload.description.strip(),
        creator_id=user.id,
        is_deleted=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_workflow", "create", f"created knowledge workflow {row.name}")
    return _out(row, db)


@router.put("/{workflow_id}")
def update_knowledge_workflow(workflow_id: int, payload: KnowledgeWorkflowUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _active_row(db, workflow_id)
    _project(db, payload.project_id, require_enabled=True)
    name = payload.name.strip()
    api_key_env = payload.api_key_env.strip()
    if not name:
        raise HTTPException(status_code=400, detail="工作流名称不能为空")
    if not api_key_env:
        raise HTTPException(status_code=400, detail="API Key 环境变量名不能为空")
    require_api_key_config(db, api_key_env)
    _require_available(db, payload.project_id, name, row.id)
    row.project_id = payload.project_id
    row.name = name
    row.api_base_url = payload.api_base_url.strip()
    row.api_key = ""
    row.api_key_env = api_key_env
    row.status = payload.status
    row.description = payload.description.strip()
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_workflow", "update", f"updated knowledge workflow {row.name}")
    return _out(row, db)


@router.delete("/{workflow_id}")
def delete_knowledge_workflow(workflow_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _active_row(db, workflow_id)
    row.is_deleted = True
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_workflow", "delete", f"deleted knowledge workflow {row.name}")
    return _out(row, db)


@router.post("/{workflow_id}/check")
def check_knowledge_workflow(workflow_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _active_row(db, workflow_id, require_enabled=True)
    try:
        result = run_workflow(row.api_base_url or get_settings().dify_api_base_url, _api_key_from_env(row), user.id, "连接测试", "")
        return {"status": "success", "answer": result["answer"], "workflow_run_id": result["workflow_run_id"]}
    except DifyWorkflowQaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
