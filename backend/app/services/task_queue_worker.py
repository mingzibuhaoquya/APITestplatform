import logging
import time

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..config import get_settings
from ..database import SessionLocal
from ..models import AiCaseGeneration, ExecutionTask
from .ai_case_generations import execute_ai_case_generation
from .executor import execute_task


logger = logging.getLogger(__name__)


def claim_next_task() -> tuple[str, int] | None:
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


def run_worker() -> None:
    settings = get_settings()
    logger.info("MySQL task queue worker started")
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
            execute_task(work_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_worker()
