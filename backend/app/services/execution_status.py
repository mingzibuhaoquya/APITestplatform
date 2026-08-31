from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ExecutionTask, TestSuite
from ..utils import dump_json, parse_json


def _parse_progress_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def ui_task_progress_is_alive(task: ExecutionTask, timeout_seconds: int | None = None) -> bool:
    timeout_seconds = timeout_seconds or max(int(get_settings().running_task_timeout_seconds or 0), 1)
    if task.target_type != "ui_case":
        return False
    summary = parse_json(task.summary_json, {})
    if not summary.get("ui_progress") or summary.get("status") != "running":
        return False
    updated_at = _parse_progress_time(summary.get("updated_at"))
    if not updated_at:
        return False
    return updated_at >= datetime.now() - timedelta(seconds=timeout_seconds)


def fail_timed_out_running_tasks(db: Session) -> int:
    timeout_seconds = max(int(get_settings().running_task_timeout_seconds or 0), 1)
    deadline = datetime.now() - timedelta(seconds=timeout_seconds)
    rows = (
        db.query(ExecutionTask)
        .filter(
            ExecutionTask.status == "running",
            ExecutionTask.started_at.isnot(None),
            ExecutionTask.started_at < deadline,
            ExecutionTask.is_deleted.is_(False),
        )
        .all()
    )
    if not rows:
        db.commit()
        return 0
    failed_count = 0
    for task in rows:
        if ui_task_progress_is_alive(task, timeout_seconds):
            continue
        task.status = "failed"
        task.ended_at = task.ended_at or datetime.now()
        summary = parse_json(task.summary_json, {})
        summary.setdefault("error", f"执行超时，已超过 {timeout_seconds} 秒")
        task.summary_json = dump_json(summary)
        failed_count += 1
        if task.target_type == "plan":
            plan = db.get(TestSuite, task.target_id)
            if plan:
                plan.last_execution_id = task.id
                plan.last_status = "failed"
                plan.last_executed_at = task.ended_at
    db.commit()
    return failed_count


def fail_orphaned_running_tasks(db: Session) -> int:
    rows = (
        db.query(ExecutionTask)
        .filter(
            ExecutionTask.status == "running",
            ExecutionTask.is_deleted.is_(False),
        )
        .all()
    )
    failed_count = 0
    for task in rows:
        task.status = "failed"
        task.ended_at = task.ended_at or datetime.now()
        summary = parse_json(task.summary_json, {})
        summary.setdefault("error", "执行进程已重启，任务中断")
        summary["status"] = "failed"
        task.summary_json = dump_json(summary)
        failed_count += 1
        if task.target_type == "plan":
            plan = db.get(TestSuite, task.target_id)
            if plan:
                plan.last_execution_id = task.id
                plan.last_status = "failed"
                plan.last_executed_at = task.ended_at
    db.commit()
    return failed_count


def mark_task_timed_out(db: Session, task_id: int) -> ExecutionTask | None:
    task = db.get(ExecutionTask, task_id)
    if not task or task.is_deleted:
        return None
    if task.status in {"queued", "running"}:
        task.status = "failed"
        task.ended_at = task.ended_at or datetime.now()
        summary = parse_json(task.summary_json, {})
        summary.setdefault("error", "执行超时")
        task.summary_json = dump_json(summary)
        if task.target_type == "plan":
            plan = db.get(TestSuite, task.target_id)
            if plan:
                plan.last_execution_id = task.id
                plan.last_status = "failed"
                plan.last_executed_at = task.ended_at
        db.commit()
        db.refresh(task)
    return task
