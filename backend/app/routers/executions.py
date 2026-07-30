from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..models import ApiDefinition, Environment, ExecutionResult, ExecutionTask, Project, ScenarioCase, TestCase, TestSuite, User
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


def _task_target_name(row: ExecutionTask, db: Session) -> str:
    if row.target_type == "plan":
        plan = db.get(TestSuite, row.target_id)
        return plan.name if plan and not plan.is_deleted else ""
    if row.target_type == "case":
        case = db.get(TestCase, row.target_id)
        return case.name if case and not case.is_deleted else ""
    scenario = db.get(ScenarioCase, row.target_id)
    return scenario.name if scenario else ""


def _task_out(row: ExecutionTask, db: Session):
    project = db.get(Project, row.project_id)
    environment = db.get(Environment, row.environment_id)
    executor = db.get(User, row.executor_id)
    return {
        "id": row.id,
        "project_id": row.project_id,
        "project_name": project.name if project and not project.is_deleted else "",
        "environment_id": row.environment_id,
        "environment_name": environment.name if environment and not environment.is_deleted else "",
        "target_type": row.target_type,
        "target_id": row.target_id,
        "target_name": _task_target_name(row, db),
        "status": row.status,
        "executor_name": executor.real_name or executor.username if executor else "",
        "started_at": fmt_time(row.started_at),
        "ended_at": fmt_time(row.ended_at),
        "summary": parse_json(row.summary_json, {}),
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


@router.get("")
def list_executions(
    name: str = "",
    status: str = "",
    target_type: str = "",
    page: int | None = None,
    page_size: int | None = None,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ExecutionTask).filter(ExecutionTask.is_deleted.is_(False))
    if status.strip():
        query = query.filter(ExecutionTask.status == status.strip())
    if target_type.strip():
        query = query.filter(ExecutionTask.target_type == target_type.strip())
    rows = query.order_by(ExecutionTask.id.desc()).all()
    name = name.strip()
    if name:
        rows = [row for row in rows if name in _task_target_name(row, db)]
    if page is None and page_size is None:
        return [_task_out(row, db) for row in rows[:100]]
    page = max(page or 1, 1)
    page_size = min(max(page_size or 10, 1), 10)
    total = len(rows)
    rows = rows[(page - 1) * page_size: page * page_size]
    return {
        "items": [_task_out(row, db) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{task_id}")
def get_execution(task_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="execution does not exist")
    results = db.query(ExecutionResult).filter(ExecutionResult.task_id == task_id).all()
    case_ids = [row.case_id for row in results if row.case_id]
    cases = db.query(TestCase).filter(TestCase.id.in_(case_ids)).all() if case_ids else []
    case_map = {row.id: row for row in cases}
    api_ids = [row.api_id for row in cases]
    apis = db.query(ApiDefinition).filter(ApiDefinition.id.in_(api_ids)).all() if api_ids else []
    api_map = {row.id: row for row in apis}
    return {
        "task": {
            "id": task.id,
            "target_name": _task_target_name(task, db),
            "status": task.status,
            "summary": parse_json(task.summary_json, {}),
            "report_html": task.report_html,
        },
        "results": [{
            "id": row.id,
            "case_id": row.case_id,
            "case_name": case_map[row.case_id].name if row.case_id in case_map else "",
            "api_name": api_map[case_map[row.case_id].api_id].name if row.case_id in case_map and case_map[row.case_id].api_id in api_map else "",
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
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="execution does not exist")
    return Response(content=task.report_html or "<h1>报告尚未生成</h1>", media_type="text/html; charset=utf-8")


@router.delete("/{task_id}")
def delete_execution(task_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="execution does not exist")
    task.is_deleted = True
    db.commit()
    return _task_out(task, db)
