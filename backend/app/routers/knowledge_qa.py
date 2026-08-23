import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import current_user
from ..models import KnowledgeProject, KnowledgeQaMessage, KnowledgeQaSession, KnowledgeWorkflow, User
from ..schemas import KnowledgeQaAskIn, KnowledgeQaSessionIn, KnowledgeQaSessionUpdate
from ..services.dify_workflow_qa import DifyWorkflowQaError, run_workflow
from ..services.operation_logs import log_operation
from ..utils import dump_json, fmt_time


router = APIRouter(prefix="/knowledge-qa", tags=["knowledge-qa"])


def _project(db: Session, project_id: int, require_enabled: bool = False) -> KnowledgeProject:
    row = db.get(KnowledgeProject, project_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=400, detail="知识库项目不存在")
    if require_enabled and row.status != "active":
        raise HTTPException(status_code=400, detail="知识库项目已禁用")
    return row


def _workflow(db: Session, workflow_id: int, require_enabled: bool = False) -> KnowledgeWorkflow:
    row = db.get(KnowledgeWorkflow, workflow_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=400, detail="工作流配置不存在")
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

def _session(db: Session, session_id: int, user: User) -> KnowledgeQaSession:
    row = db.get(KnowledgeQaSession, session_id)
    if not row or row.is_deleted or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="问答会话不存在")
    return row


def _session_out(row: KnowledgeQaSession, db: Session) -> dict:
    project = db.get(KnowledgeProject, row.project_id)
    workflow = db.get(KnowledgeWorkflow, row.workflow_id)
    return {
        "id": row.id,
        "project_id": row.project_id,
        "project_name": project.name if project and not project.is_deleted else "",
        "workflow_id": row.workflow_id,
        "workflow_name": workflow.name if workflow and not workflow.is_deleted else "",
        "title": row.title,
        "status": row.status,
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


def _message_out(row: KnowledgeQaMessage) -> dict:
    return {
        "id": row.id,
        "session_id": row.session_id,
        "role": row.role,
        "content": row.content,
        "error_message": row.error_message,
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


def _build_history(db: Session, session_id: int, limit_rounds: int = 5) -> str:
    rows = db.query(KnowledgeQaMessage).filter(
        KnowledgeQaMessage.session_id == session_id,
        KnowledgeQaMessage.error_message == "",
    ).order_by(KnowledgeQaMessage.id.desc()).limit(limit_rounds * 2).all()
    rows = list(reversed(rows))
    lines = []
    for row in rows:
        role_name = "用户" if row.role == "user" else "助手"
        content = row.content.strip()
        if content:
            lines.append(f"{role_name}：{content}")
    return "\n".join(lines)


def _default_title(question: str) -> str:
    value = question.strip().replace("\n", " ")
    return value[:40] or "新会话"


@router.get("/sessions")
def list_sessions(
    project_id: int | None = None,
    workflow_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(KnowledgeQaSession).filter(
        KnowledgeQaSession.user_id == user.id,
        KnowledgeQaSession.is_deleted.is_(False),
    )
    if project_id:
        query = query.filter(KnowledgeQaSession.project_id == project_id)
    if workflow_id:
        query = query.filter(KnowledgeQaSession.workflow_id == workflow_id)
    total = query.count()
    rows = query.order_by(KnowledgeQaSession.update_date.desc(), KnowledgeQaSession.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_session_out(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/sessions", status_code=201)
def create_session(payload: KnowledgeQaSessionIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _project(db, payload.project_id, require_enabled=True)
    workflow = _workflow(db, payload.workflow_id, require_enabled=True)
    if workflow.project_id != payload.project_id:
        raise HTTPException(status_code=400, detail="工作流不属于所选知识库项目")
    title = payload.title.strip() or "新会话"
    row = KnowledgeQaSession(
        user_id=user.id,
        project_id=payload.project_id,
        workflow_id=payload.workflow_id,
        title=title[:128],
        status="active",
        is_deleted=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_qa", "create_session", f"created knowledge qa session {row.title}")
    return _session_out(row, db)


@router.put("/sessions/{session_id}")
def update_session(session_id: int, payload: KnowledgeQaSessionUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _session(db, session_id, user)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="会话标题不能为空")
    row.title = title[:128]
    db.commit()
    db.refresh(row)
    return _session_out(row, db)


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _session(db, session_id, user)
    row.is_deleted = True
    db.commit()
    db.refresh(row)
    log_operation(db, user, "knowledge_qa", "delete_session", f"deleted knowledge qa session {row.title}")
    return _session_out(row, db)


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _session(db, session_id, user)
    rows = db.query(KnowledgeQaMessage).filter(KnowledgeQaMessage.session_id == session_id).order_by(KnowledgeQaMessage.id.asc()).all()
    return [_message_out(row) for row in rows]


@router.post("/sessions/{session_id}/ask")
def ask(session_id: int, payload: KnowledgeQaAskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = _session(db, session_id, user)
    if session.status != "active":
        raise HTTPException(status_code=400, detail="问答会话已禁用")
    workflow = _workflow(db, session.workflow_id, require_enabled=True)
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="请输入问题")
    chat_history = _build_history(db, session.id)

    user_message = KnowledgeQaMessage(session_id=session.id, role="user", content=question)
    db.add(user_message)
    if session.title == "新会话":
        session.title = _default_title(question)
    db.commit()
    db.refresh(user_message)

    try:
        result = run_workflow(workflow.api_base_url or get_settings().dify_api_base_url, _api_key_from_env(workflow), user.id, question, chat_history)
        assistant_message = KnowledgeQaMessage(
            session_id=session.id,
            role="assistant",
            content=result["answer"],
            dify_workflow_run_id=result["workflow_run_id"],
            dify_task_id=result["task_id"],
            raw_response_json=dump_json(result["raw_response"]),
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        return {"user_message": _message_out(user_message), "assistant_message": _message_out(assistant_message)}
    except DifyWorkflowQaError as exc:
        assistant_message = KnowledgeQaMessage(
            session_id=session.id,
            role="assistant",
            content="",
            error_message=str(exc)[:4000],
        )
        db.add(assistant_message)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
