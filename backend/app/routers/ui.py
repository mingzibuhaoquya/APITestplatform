from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import AiSetting, Environment, ExecutionResult, ExecutionTask, Project, UiTestCase, User
from ..schemas import AiSettingIn, UiTestCaseIn, UiTestCaseUpdate
from ..services.operation_logs import log_operation
from ..utils import dump_json, fmt_time, parse_json


router = APIRouter(tags=["ui-tests"])


def _base(row):
    data = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    data["create_date"] = fmt_time(row.create_date)
    data["update_date"] = fmt_time(row.update_date)
    return data


def _active_project(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _active_environment(environment_id: int, project_id: int, db: Session) -> Environment:
    environment = db.get(Environment, environment_id)
    if not environment or environment.is_deleted:
        raise HTTPException(status_code=404, detail="环境不存在")
    if environment.project_id != project_id:
        raise HTTPException(status_code=400, detail="环境不属于所选项目")
    return environment


def _ui_case_out(row: UiTestCase, db: Session):
    project = db.get(Project, row.project_id)
    environment = db.get(Environment, row.environment_id)
    return {
        **_base(row),
        "project_name": project.name if project and not project.is_deleted else "",
        "environment_name": environment.name if environment and not environment.is_deleted else "",
        "steps": parse_json(row.steps_json, []),
    }


def _validate_case(payload: UiTestCaseIn | UiTestCaseUpdate, db: Session):
    _active_project(payload.project_id, db)
    _active_environment(payload.environment_id, payload.project_id, db)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="UI用例名称不能为空")
    if payload.wait_after_load_ms < 0 or payload.wait_after_load_ms > 60000:
        raise HTTPException(status_code=400, detail="页面额外等待时间需在 0 到 60000ms 之间")
    steps = [item.model_dump() for item in payload.steps]
    return name, steps


@router.get("/ui-cases")
def list_ui_cases(
    project_id: int | None = None,
    environment_id: int | None = None,
    name: str = "",
    status: str = "",
    page: int | None = None,
    page_size: int | None = None,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(UiTestCase).filter(UiTestCase.is_deleted.is_(False))
    if project_id:
        query = query.filter(UiTestCase.project_id == project_id)
    if environment_id:
        query = query.filter(UiTestCase.environment_id == environment_id)
    if name.strip():
        query = query.filter(UiTestCase.name.like(f"%{name.strip()}%"))
    if status.strip():
        query = query.filter(UiTestCase.status == status.strip())
    ordered = query.order_by(UiTestCase.id.desc())
    if page is None and page_size is None:
        return [_ui_case_out(row, db) for row in ordered.limit(100).all()]
    page = max(page or 1, 1)
    page_size = min(max(page_size or 10, 1), 20)
    total = query.count()
    rows = ordered.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_ui_case_out(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/ui-cases")
def create_ui_case(payload: UiTestCaseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name, steps = _validate_case(payload, db)
    row = UiTestCase(
        project_id=payload.project_id,
        environment_id=payload.environment_id,
        name=name,
        start_url=payload.start_url.strip(),
        description=payload.description.strip(),
        steps_json=dump_json(steps),
        status=payload.status,
        headless=payload.headless,
        wait_until=payload.wait_until,
        wait_after_load_ms=payload.wait_after_load_ms,
        is_deleted=False,
        maintainer_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_operation(db, user, "ui", "create", f"created ui case {row.name}")
    return _ui_case_out(row, db)


@router.put("/ui-cases/{case_id}")
def update_ui_case(case_id: int, payload: UiTestCaseUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(UiTestCase, case_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="UI用例不存在")
    name, steps = _validate_case(payload, db)
    row.project_id = payload.project_id
    row.environment_id = payload.environment_id
    row.name = name
    row.start_url = payload.start_url.strip()
    row.description = payload.description.strip()
    row.steps_json = dump_json(steps)
    row.status = payload.status
    row.headless = payload.headless
    row.wait_until = payload.wait_until
    row.wait_after_load_ms = payload.wait_after_load_ms
    db.commit()
    db.refresh(row)
    log_operation(db, user, "ui", "update", f"updated ui case {row.name}")
    return _ui_case_out(row, db)


@router.delete("/ui-cases/{case_id}")
def delete_ui_case(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(UiTestCase, case_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="UI用例不存在")
    row.is_deleted = True
    db.commit()
    db.refresh(row)
    log_operation(db, user, "ui", "delete", f"deleted ui case {row.name}")
    return _ui_case_out(row, db)


@router.post("/ui-cases/{case_id}/execute")
def execute_ui_case(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(UiTestCase, case_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="UI用例不存在")
    if row.status != "active":
        raise HTTPException(status_code=400, detail="UI用例未启用")
    task = ExecutionTask(executor_id=user.id, project_id=row.project_id, environment_id=row.environment_id, target_type="ui_case", target_id=row.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    log_operation(db, user, "ui", "execute", f"executed ui case {row.name}, task {task.id}")
    return {"id": task.id, "status": task.status}


@router.get("/ui-executions/{task_id}")
def get_ui_execution(task_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task or task.is_deleted or task.target_type != "ui_case":
        raise HTTPException(status_code=404, detail="UI执行记录不存在")
    case = db.get(UiTestCase, task.target_id)
    results = db.query(ExecutionResult).filter(ExecutionResult.task_id == task.id).all()
    return {
        "task": {
            "id": task.id,
            "target_name": case.name if case else "",
            "status": task.status,
            "summary": parse_json(task.summary_json, {}),
            "report_html": task.report_html,
            "create_date": fmt_time(task.create_date),
            "update_date": fmt_time(task.update_date),
        },
        "results": [{
            "id": row.id,
            "case_id": row.case_id,
            "case_name": case.name if case else "",
            "status": row.status,
            "request_snapshot": parse_json(row.request_snapshot_json, {}),
            "response_snapshot": parse_json(row.response_snapshot_json, {}),
            "assertion_results": parse_json(row.assertion_results_json, []),
            "duration_ms": row.duration_ms,
            "error_message": row.error_message,
        } for row in results],
    }


@router.get("/ui-artifacts/{filename}")
def get_ui_artifact(filename: str, _: User = Depends(current_user)):
    root = Path("logs/ui-artifacts").resolve()
    path = (root / filename).resolve()
    if root not in path.parents or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="截图不存在")
    return FileResponse(path)


def _ai_setting_out(row: AiSetting | None):
    if not row:
        return {"provider_url": "", "model_name": "", "api_key": "", "status": "disabled", "description": ""}
    masked_key = "******" if row.api_key else ""
    return {
        "id": row.id,
        "provider_url": row.provider_url,
        "model_name": row.model_name,
        "api_key": masked_key,
        "status": row.status,
        "description": row.description,
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


@router.get("/ai-settings")
def get_ai_setting(_: User = Depends(current_user), db: Session = Depends(get_db)):
    return _ai_setting_out(db.query(AiSetting).order_by(AiSetting.id.asc()).first())


@router.put("/ai-settings")
def update_ai_setting(payload: AiSettingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.query(AiSetting).order_by(AiSetting.id.asc()).first()
    if not row:
        row = AiSetting()
        db.add(row)
    row.provider_url = payload.provider_url.strip()
    row.model_name = payload.model_name.strip()
    if payload.api_key and payload.api_key != "******":
        row.api_key = payload.api_key
    row.status = payload.status
    row.description = payload.description.strip()
    db.commit()
    db.refresh(row)
    log_operation(db, user, "ui", "update", "updated ai setting")
    return _ai_setting_out(row)
