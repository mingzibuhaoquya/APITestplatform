import logging
import time

from sqlalchemy import select

from ..config import get_settings
from ..database import SessionLocal
from ..models import ExecutionTask
from .executor import execute_task
from .ui_executor import execute_ui_task


logger = logging.getLogger(__name__)


def claim_next_task() -> int | None:
    db = SessionLocal()
    try:
        with db.begin():
            task = db.scalars(
                select(ExecutionTask)
                .where(ExecutionTask.status == "queued")
                .order_by(ExecutionTask.id.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            ).first()
            if not task:
                return None
            task.status = "running"
            return task.id
    finally:
        db.close()


def run_worker() -> None:
    settings = get_settings()
    logger.info("MySQL task queue worker started")
    while True:
        task_id = claim_next_task()
        if task_id is None:
            time.sleep(settings.queue_poll_interval_seconds)
            continue
        logger.info("Executing task %s", task_id)
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_worker()
