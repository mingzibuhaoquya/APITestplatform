import logging
import time

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..config import get_settings
from ..database import SessionLocal
from ..models import AiCaseGeneration, ExecutionTask
from .ai_case_generations import execute_ai_case_generation
from .execution_status import fail_orphaned_running_tasks, fail_timed_out_running_tasks
from .executor import execute_task
from .ui_executor import execute_ui_task


logger = logging.getLogger(__name__)


def claim_next_task() -> tuple[str, int] | None:
    db = SessionLocal()
    try:
        fail_timed_out_running_tasks(db)
        with db.begin():
            task = db.scalars(
                select(ExecutionTask)
                .where(ExecutionTask.status == "queued")
                .order_by(ExecutionTask.id.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            ).first()
            if not task:
                generation = db.scalars(
                    select(AiCaseGeneration)
                    .where(AiCaseGeneration.status == "queued")
                    .order_by(AiCaseGeneration.id.asc())
                    .with_for_update(skip_locked=True)
                    .limit(1)
                ).first()
                if not generation:
                    return None
                generation.status = "running"
                return "ai_generation", generation.id
            task.status = "running"
            return "execution", task.id
    finally:
        db.close()


def _run_execution(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(ExecutionTask, task_id)
        target_type = task.target_type if task else ""
    finally:
        db.close()
    if target_type == "ui_case":
        execute_ui_task(task_id)
    else:
        execute_task(task_id)


def run_worker() -> None:
    settings = get_settings()
    logger.info("MySQL task queue worker started")
    db = SessionLocal()
    try:
        failed_count = fail_orphaned_running_tasks(db)
        if failed_count:
            logger.warning("Marked %s orphaned running tasks as failed", failed_count)
    finally:
        db.close()
    while True:
        try:
            work = claim_next_task()
        except SQLAlchemyError:
            logger.exception("Unable to claim queued work; retrying")
            time.sleep(settings.queue_poll_interval_seconds)
            continue
        if work is None:
            time.sleep(settings.queue_poll_interval_seconds)
            continue
        work_type, work_id = work
        logger.info("Executing %s %s", work_type, work_id)
        if work_type == "ai_generation":
            execute_ai_case_generation(work_id)
        else:
            _run_execution(work_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_worker()
