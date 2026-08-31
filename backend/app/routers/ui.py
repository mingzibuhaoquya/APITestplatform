import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import AiSetting, Environment, ExecutionResult, ExecutionTask, Project, UiTestCase, User
from ..schemas import AiSettingIn, UiGenerateStepsIn, UiTestCaseIn, UiTestCaseUpdate
from ..services.execution_status import fail_timed_out_running_tasks, ui_task_progress_is_alive
from ..services.operation_logs import log_operation
from ..services.report import build_html_report
from ..services.ui_executor import UiResultView
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


def _ui_task_status(task: ExecutionTask | None) -> str:
    if not task:
        return ""
    summary = parse_json(task.summary_json, {})
    if summary.get("ui_progress") and summary.get("status") == "running" and ui_task_progress_is_alive(task):
        return "running"
    return task.status


def _ui_progress_error(task: ExecutionTask, summary: dict[str, Any]) -> str:
    for key in ("error", "message"):
        value = str(summary.get(key) or "").strip()
        if value:
            return value
    for item in reversed(summary.get("agent_steps") or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "") in {"failed", "error"}:
            return str(item.get("message") or item.get("error") or "UI执行步骤失败")
    if task.status in {"failed", "error"} and summary.get("ui_progress"):
        updated_at = summary.get("updated_at") or "-"
        return f"UI执行已中断或超时，最后进度更新时间：{updated_at}"
    return ""


def _ui_task_summary(task: ExecutionTask) -> dict[str, Any]:
    summary = parse_json(task.summary_json, {})
    error = _ui_progress_error(task, summary)
    if error and not summary.get("error"):
        summary["error"] = error
    return summary


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
        "last_status": _ui_task_status(last_task),
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
        browser_channel=payload.browser_channel,
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
    row.browser_channel = payload.browser_channel
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
    project = db.get(Project, task.project_id)
    environment = db.get(Environment, task.environment_id)
    executor = db.get(User, task.executor_id)
    results = db.query(ExecutionResult).filter(ExecutionResult.task_id == task.id).all()
    summary = _ui_task_summary(task)
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
    if not result_items and (summary.get("ui_progress") or (case and case.execution_mode == "ai" and task.status in {"queued", "running"})):
        result_items.append({
            "id": f"progress-{task.id}",
            "case_id": task.target_id,
            "case_name": case.name if case else "",
            "status": _ui_task_status(task),
            "request_snapshot": {
                "mode": "ai",
                "browser": case.browser_channel if case else "chromium",
                "headless": case.headless is not False if case else True,
                "test_goal": case.test_goal if case else "",
                "test_data": parse_json(case.test_data_json, {}) if case else {},
                "assertion_goal": case.assertion_goal if case else "",
            },
            "response_snapshot": {
                "status": summary.get("status") or task.status,
                "message": summary.get("message") or summary.get("error") or "AI执行已提交，正在等待执行进度",
                "agent_steps": summary.get("agent_steps") or [],
                "screenshots": summary.get("screenshots") or [],
                "token_usage": summary.get("token_usage") or {},
                "updated_at": summary.get("updated_at"),
            },
            "assertion_results": [],
            "duration_ms": 0,
            "error_message": summary.get("error") or summary.get("message") or "",
        })
    report_html = _build_ui_execution_report_html(db, task, case, results, project, environment, executor)
    return {
        "task": {
            "id": task.id,
            "target_name": case.name if case else "",
            "project_name": project.name if project and not project.is_deleted else "",
            "environment_name": environment.name if environment and not environment.is_deleted else "",
            "executor_name": executor.real_name or executor.username if executor else "",
            "status": _ui_task_status(task),
            "summary": summary,
            "report_html": report_html,
            "started_at": fmt_time(task.started_at),
            "ended_at": fmt_time(task.ended_at),
            "create_date": fmt_time(task.create_date),
            "update_date": fmt_time(task.update_date),
        },
        "results": result_items,
    }


@router.post("/ui-executions/{task_id}/stop")
def stop_ui_execution(task_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task or task.is_deleted or task.target_type != "ui_case":
        raise HTTPException(status_code=404, detail="UI执行记录不存在")
    if task.status not in {"queued", "running"}:
        return {"id": task.id, "status": _ui_task_status(task), "message": "任务已结束，无需停止"}
    summary = _ui_task_summary(task)
    summary["stop_requested"] = True
    summary["status"] = "stopped"
    summary["message"] = "用户手动停止任务"
    task.status = "stopped"
    task.ended_at = datetime.now()
    task.summary_json = dump_json(summary)
    db.commit()
    db.refresh(task)
    log_operation(db, user, "ui", "stop", f"stopped ui task {task.id}")
    return {"id": task.id, "status": "stopped", "message": "已发送停止请求"}


def _build_ui_execution_report_html(
    db: Session,
    task: ExecutionTask,
    case: UiTestCase | None,
    results: list[ExecutionResult],
    project: Project | None,
    environment: Environment | None,
    executor: User | None,
) -> str:
    if not case or not results:
        return task.report_html
    task.project_name = project.name if project and not project.is_deleted else ""
    task.environment_name = environment.name if environment and not environment.is_deleted else ""
    task.executor_name = executor.real_name or executor.username if executor else ""
    html = build_html_report(task, [UiResultView(row, case) for row in results], case.name)
    if html and html != task.report_html:
        task.report_html = html
        db.commit()
    return html or task.report_html


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
        if action not in {"click", "dblclick", "fill", "select", "wait", "assert_text", "screenshot"}:
            continue
        locator_type = "css"
        target = str(item.get("target") or "")
        if action in {"click", "dblclick", "fill", "select"}:
            locator_type, target = _solidified_locator(item)
        if action == "assert_text":
            locator_type = "text"
            target = str(item.get("value") or item.get("target") or item.get("message") or "")
        value = _solidified_step_value(item)
        rows.append(
            {
                "action": action,
                "locator_type": locator_type,
                "target": target,
                "value": value,
                "description": str(item.get("reason") or item.get("message") or ""),
            }
        )
        wait_ms = _solidified_pace_wait_ms(item)
        if wait_ms:
            rows.append(
                {
                    "action": "wait",
                    "locator_type": "css",
                    "target": "",
                    "value": str(wait_ms),
                    "description": f"沿用AI执行节奏，等待 {wait_ms}ms",
                }
            )
    if rows and rows[-1].get("action") != "screenshot":
        rows.append(
            {
                "action": "screenshot",
                "locator_type": "css",
                "target": "",
                "value": "",
                "description": "保存最终页面截图",
            }
        )
    return rows


def _solidified_step_value(item: dict) -> str:
    action = str(item.get("action") or "")
    if action == "wait":
        wait_ms = _solidified_wait_value(item)
        return str(wait_ms) if wait_ms else str(item.get("value") or "")
    return str(item.get("value") or "")


def _solidified_wait_value(item: dict) -> int:
    value = str(item.get("value") or "").strip()
    if value.isdigit():
        number = int(value)
        return number * 1000 if 0 < number < 1000 else number
    message = str(item.get("message") or "")
    match = re.search(r"(\d+)\s*ms", message)
    if match:
        return int(match.group(1))
    try:
        return int(item.get("duration_ms") or 0)
    except (TypeError, ValueError):
        return 0


def _solidified_pace_wait_ms(item: dict) -> int:
    if str(item.get("status") or "") != "passed":
        return 0
    action = str(item.get("action") or "")
    if action not in {"click", "dblclick", "fill", "select"}:
        return 0
    try:
        duration_ms = int(item.get("duration_ms") or 0)
    except (TypeError, ValueError):
        duration_ms = 0
    if duration_ms <= 0:
        return 0
    return min(max(duration_ms, 500), 10000)


def _solidified_locator(item: dict) -> tuple[str, str]:
    locator_type = str(item.get("locator_type") or "").strip()
    target = str(item.get("target") or "").strip()
    if locator_type in {"css", "xpath", "text", "placeholder", "role"} and target:
        return locator_type, target
    return "ai", _solidified_target(item)


def _solidified_target(item: dict) -> str:
    reason = str(item.get("reason") or "").strip()
    message = str(item.get("message") or "").strip()
    value = str(item.get("value") or "").strip()
    action = str(item.get("action") or "").strip()
    for text in (reason, message):
        if text and text != "通过":
            return text
    if action == "fill":
        return f"需要输入 {value} 的输入框" if value else "需要输入内容的输入框"
    if action == "select":
        return f"需要选择 {value} 的下拉框" if value else "需要选择的下拉框"
    if action in {"click", "dblclick"}:
        return "需要点击的按钮或元素"
    return ""


@router.get("/ui-artifacts/{filename}")
def get_ui_artifact(filename: str, _: User = Depends(current_user)):
    root = Path("logs/ui-artifacts").resolve()
    path = (root / filename).resolve()
    if root not in path.parents or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="截图不存在")
    return FileResponse(path)


def _ai_setting_out(row: AiSetting | None):
    if not row:
        return {"id": None, "name": "", "provider_url": "", "model_name": "", "api_key": "", "status": "disabled", "is_default": False, "description": ""}
    masked_key = "******" if row.api_key else ""
    return {
        "id": row.id,
        "name": row.name,
        "provider_url": row.provider_url,
        "model_name": row.model_name,
        "api_key": masked_key,
        "status": row.status,
        "is_default": row.is_default,
        "description": row.description,
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


@router.get("/ai-settings")
def get_ai_setting(_: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(AiSetting).order_by(AiSetting.is_default.desc(), AiSetting.id.asc()).all()
    active = (
        db.query(AiSetting)
        .filter(AiSetting.status == "active", AiSetting.provider_url != "", AiSetting.model_name != "")
        .order_by(AiSetting.is_default.desc(), AiSetting.id.asc())
        .first()
    )
    data = _ai_setting_out(active or (rows[0] if rows else None))
    data["items"] = [_ai_setting_out(row) for row in rows]
    return data


@router.put("/ai-settings")
def update_ai_setting(payload: AiSettingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(AiSetting, payload.id) if payload.id else None
    if payload.id and not row:
        raise HTTPException(status_code=404, detail="AI配置不存在")
    if row is None:
        row = AiSetting()
        db.add(row)
    name = payload.name.strip() or payload.model_name.strip() or "AI配置"
    row.name = name
    row.provider_url = payload.provider_url.strip()
    row.model_name = payload.model_name.strip()
    if payload.api_key and payload.api_key != "******":
        row.api_key = payload.api_key
    row.status = payload.status
    row.is_default = payload.is_default
    row.description = payload.description.strip()
    if row.is_default:
        db.query(AiSetting).filter(AiSetting.id != (row.id or 0)).update({AiSetting.is_default: False})
    db.commit()
    db.refresh(row)
    log_operation(db, user, "ui", "update", "updated ai setting")
    return _ai_setting_out(row)


@router.post("/ai-settings/{setting_id}/default")
def set_default_ai_setting(setting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(AiSetting, setting_id)
    if not row:
        raise HTTPException(status_code=404, detail="AI配置不存在")
    db.query(AiSetting).filter(AiSetting.id != setting_id).update({AiSetting.is_default: False})
    row.is_default = True
    db.commit()
    db.refresh(row)
    log_operation(db, user, "ui", "update", f"set default ai setting {row.name}")
    return _ai_setting_out(row)


@router.delete("/ai-settings/{setting_id}")
def delete_ai_setting(setting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(AiSetting, setting_id)
    if not row:
        raise HTTPException(status_code=404, detail="AI配置不存在")
    was_default = row.is_default
    db.delete(row)
    db.flush()
    if was_default:
        next_row = db.query(AiSetting).order_by(AiSetting.id.asc()).first()
        if next_row:
            next_row.is_default = True
    db.commit()
    log_operation(db, user, "ui", "delete", f"deleted ai setting {row.name}")
    return {"success": True}


@router.post("/ai-settings/test")
def test_ai_setting(payload: AiSettingIn, _: User = Depends(current_user), db: Session = Depends(get_db)):
    provider_url = payload.provider_url.strip()
    model_name = payload.model_name.strip()
    api_key = payload.api_key
    if api_key in {"", "******"}:
        current = db.get(AiSetting, payload.id) if payload.id else db.query(AiSetting).order_by(AiSetting.is_default.desc(), AiSetting.id.asc()).first()
        api_key = current.api_key if current else ""
    if not provider_url:
        raise HTTPException(status_code=400, detail="请先填写模型服务地址")
    if not model_name:
        raise HTTPException(status_code=400, detail="请先填写模型名称")

    url = _chat_completions_url(provider_url)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "你只负责测试连接。"},
            {"role": "user", "content": "请只回复一个字：是"},
        ],
        "temperature": 0,
        "max_tokens": 8,
    }
    try:
        response = httpx.post(url, json=body, headers=headers, timeout=15)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=400, detail=f"AI连接失败：{exc}；{_ai_connection_error_hint(url, exc)}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"AI连接失败：HTTP {response.status_code}，{_response_preview(response)}")
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"AI连接失败：响应不是合法JSON，{response.text[:300]}") from exc
    message = data.get("choices", [{}])[0].get("message", {}) or {}
    content = str(message.get("content") or message.get("reasoning_content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail=f"AI连接失败：响应中没有模型回复，{_compact_value(data)}")
    return {"success": True, "message": "连接成功", "reply": content[:20]}


def _chat_completions_url(provider_url: str) -> str:
    value = (provider_url or "").strip().rstrip("/")
    if value.endswith("/chat/completions"):
        return value
    if value in {"https://api.deepseek.com", "http://api.deepseek.com"}:
        value = f"{value}/v1"
    return f"{value}/chat/completions"


def _response_preview(response: httpx.Response) -> str:
    try:
        return _compact_value(response.json())
    except json.JSONDecodeError:
        return response.text[:500]


def _compact_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)[:500]


def _ai_connection_error_hint(url: str, exc: httpx.RequestError) -> str:
    text = str(exc).lower()
    if "unexpected_eof_while_reading" in text or "eof occurred in violation of protocol" in text or "wrong version number" in text:
        if url.startswith("https://"):
            return "SSL握手失败，请优先确认模型服务地址是否实际只支持 http://；如果必须使用 https，请检查模型网关证书、反向代理 TLS 配置和公司代理。"
        return "SSL/TLS连接异常，请检查模型网关证书、反向代理 TLS 配置和公司代理。"
    if "certificate" in text or "cert" in text:
        return "证书校验失败，请检查证书是否过期、域名是否匹配，或改用受信任的模型网关地址。"
    if "name or service not known" in text or "getaddrinfo" in text or "nodename nor servname" in text:
        return "域名解析失败，请检查服务地址、DNS、代理或容器网络配置。"
    if "connection refused" in text or "connecterror" in text:
        return "服务拒绝连接，请确认模型服务已启动、端口正确，并且容器能访问该地址。"
    if "timed out" in text or "timeout" in text:
        return "请求超时，请检查网络连通性、模型服务负载，或稍后重试。"
    return "请检查模型服务地址、网络连通性、代理和服务器 DNS。"
