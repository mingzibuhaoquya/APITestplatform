from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import AiSetting, Environment, ExecutionResult, ExecutionTask, Project, UiTestCase, User
from ..schemas import AiSettingIn, UiGenerateStepsIn, UiTestCaseIn, UiTestCaseUpdate
from ..services.execution_status import fail_timed_out_running_tasks
from ..services.operation_logs import log_operation
from ..services.ui_step_generator import generate_ui_steps
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
    last_task = (
        db.query(ExecutionTask)
        .filter(
            ExecutionTask.target_type == "ui_case",
            ExecutionTask.target_id == row.id,
            ExecutionTask.is_deleted.is_(False),
        )
        .order_by(ExecutionTask.id.desc())
        .first()
    )
    return {
        **_base(row),
        "project_name": project.name if project and not project.is_deleted else "",
        "environment_name": environment.name if environment and not environment.is_deleted else "",
        "test_data": parse_json(row.test_data_json, {}),
        "steps": parse_json(row.steps_json, []),
        "last_task_id": last_task.id if last_task else None,
        "last_status": last_task.status if last_task else "",
        "last_executed_at": fmt_time(last_task.create_date) if last_task else None,
    }


def _validate_case(payload: UiTestCaseIn | UiTestCaseUpdate, db: Session):
    _active_project(payload.project_id, db)
    _active_environment(payload.environment_id, payload.project_id, db)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="UI用例名称不能为空")
    if payload.wait_after_load_ms < 0 or payload.wait_after_load_ms > 60000:
        raise HTTPException(status_code=400, detail="页面额外等待时间需在 0 到 60000ms 之间")
    if payload.max_steps < 1 or payload.max_steps > 100:
        raise HTTPException(status_code=400, detail="AI最大步骤数需在 1 到 100 之间")
    if payload.step_timeout_ms < 1000 or payload.step_timeout_ms > 120000:
        raise HTTPException(status_code=400, detail="单步超时时间需在 1000 到 120000ms 之间")
    if payload.execution_mode == "ai" and not payload.test_goal.strip():
        raise HTTPException(status_code=400, detail="AI模式请填写测试目标")
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
        execution_mode=payload.execution_mode,
        test_goal=payload.test_goal.strip(),
        test_data_json=dump_json(payload.test_data),
        assertion_goal=payload.assertion_goal.strip(),
        max_steps=payload.max_steps,
        step_timeout_ms=payload.step_timeout_ms,
        allow_ai_actions=payload.allow_ai_actions,
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


@router.post("/ui-cases/generate-steps")
def generate_ui_case_steps(payload: UiGenerateStepsIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    steps = generate_ui_steps(
        db,
        payload.prompt,
        payload.start_url,
        [item.model_dump() for item in payload.existing_steps],
    )
    if not steps:
        raise HTTPException(status_code=400, detail="未能从描述中生成可执行步骤")
    log_operation(db, user, "ui", "generate_steps", "generated ui steps from natural language")
    return {"steps": steps}


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
    row.execution_mode = payload.execution_mode
    row.test_goal = payload.test_goal.strip()
    row.test_data_json = dump_json(payload.test_data)
    row.assertion_goal = payload.assertion_goal.strip()
    row.max_steps = payload.max_steps
    row.step_timeout_ms = payload.step_timeout_ms
    row.allow_ai_actions = payload.allow_ai_actions
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
    fail_timed_out_running_tasks(db)
    task = db.get(ExecutionTask, task_id)
    if not task or task.is_deleted or task.target_type != "ui_case":
        raise HTTPException(status_code=404, detail="UI执行记录不存在")
    case = db.get(UiTestCase, task.target_id)
    results = db.query(ExecutionResult).filter(ExecutionResult.task_id == task.id).all()
    summary = parse_json(task.summary_json, {})
    result_items = [{
        "id": row.id,
        "case_id": row.case_id,
        "case_name": case.name if case else "",
        "status": row.status,
        "request_snapshot": parse_json(row.request_snapshot_json, {}),
        "response_snapshot": parse_json(row.response_snapshot_json, {}),
        "assertion_results": parse_json(row.assertion_results_json, []),
        "duration_ms": row.duration_ms,
        "error_message": row.error_message,
    } for row in results]
    if not result_items and summary.get("ui_progress"):
        result_items.append({
            "id": f"progress-{task.id}",
            "case_id": task.target_id,
            "case_name": case.name if case else "",
            "status": task.status,
            "request_snapshot": {
                "mode": "ai",
                "test_goal": case.test_goal if case else "",
            },
            "response_snapshot": {
                "agent_steps": summary.get("agent_steps") or [],
                "screenshots": summary.get("screenshots") or [],
                "updated_at": summary.get("updated_at"),
            },
            "assertion_results": [],
            "duration_ms": 0,
            "error_message": summary.get("message") or "",
        })
    return {
        "task": {
            "id": task.id,
            "target_name": case.name if case else "",
            "status": task.status,
            "summary": summary,
            "report_html": task.report_html,
            "create_date": fmt_time(task.create_date),
            "update_date": fmt_time(task.update_date),
        },
        "results": result_items,
    }


@router.post("/ui-executions/{task_id}/solidify")
def solidify_ui_execution(task_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task or task.is_deleted or task.target_type != "ui_case":
        raise HTTPException(status_code=404, detail="UI执行记录不存在")
    case = db.get(UiTestCase, task.target_id)
    if not case or case.is_deleted:
        raise HTTPException(status_code=404, detail="UI用例不存在")
    result = db.query(ExecutionResult).filter(ExecutionResult.task_id == task.id).order_by(ExecutionResult.id.desc()).first()
    if not result:
        raise HTTPException(status_code=400, detail="没有可固化的执行结果")
    agent_steps = parse_json(result.response_snapshot_json, {}).get("agent_steps", [])
    fixed_steps = _solidified_steps(agent_steps)
    if not fixed_steps:
        raise HTTPException(status_code=400, detail="没有可固化的AI步骤")
    case.execution_mode = "advanced"
    case.steps_json = dump_json(fixed_steps)
    db.commit()
    db.refresh(case)
    log_operation(db, user, "ui", "solidify", f"solidified ui case {case.name} from task {task.id}")
    return _ui_case_out(case, db)


def _solidified_steps(agent_steps: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for item in agent_steps:
        action = str(item.get("action") or "")
        if action not in {"click", "fill", "select", "wait", "assert_text", "screenshot"}:
            continue
        rows.append(
            {
                "action": action,
                "locator_type": str(item.get("locator_type") or "xpath") if action not in {"wait", "screenshot"} else "css",
                "target": str(item.get("target") or ""),
                "value": str(item.get("value") or ""),
                "description": str(item.get("reason") or item.get("message") or ""),
            }
        )
    return rows


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
