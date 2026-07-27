from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..models import ExecutionResult, ExecutionTask, User
from ..schemas import ExecutionCreate
from ..utils import fmt_time, parse_json


router = APIRouter(prefix="/executions", tags=["executions"])


@router.post("")
def create_execution(payload: ExecutionCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = ExecutionTask(executor_id=user.id, project_id=payload.project_id, environment_id=payload.environment_id, target_type=payload.target_type, target_id=payload.target_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"id": task.id, "status": task.status}


@router.get("")
def list_executions(_: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(ExecutionTask).order_by(ExecutionTask.id.desc()).limit(100).all()
    return [{
        "id": row.id,
        "project_id": row.project_id,
        "environment_id": row.environment_id,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "status": row.status,
        "started_at": fmt_time(row.started_at),
        "ended_at": fmt_time(row.ended_at),
        "summary": parse_json(row.summary_json, {}),
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    } for row in rows]


@router.get("/{task_id}")
def get_execution(task_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    results = db.query(ExecutionResult).filter(ExecutionResult.task_id == task_id).all()
    return {
        "task": {
            "id": task.id,
            "status": task.status,
            "summary": parse_json(task.summary_json, {}),
            "report_html": task.report_html,
        },
        "results": [{
            "id": row.id,
            "case_id": row.case_id,
            "status": row.status,
            "request_snapshot": parse_json(row.request_snapshot_json, {}),
            "response_snapshot": parse_json(row.response_snapshot_json, {}),
            "assertion_results": parse_json(row.assertion_results_json, []),
            "duration_ms": row.duration_ms,
            "error_message": row.error_message,
        } for row in results],
    }


@router.get("/{task_id}/report", response_class=Response)
def report(task_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    return Response(content=task.report_html or "<h1>报告尚未生成</h1>", media_type="text/html; charset=utf-8")
