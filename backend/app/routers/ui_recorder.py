from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Environment, User
from ..services.operation_logs import log_operation
from ..services.ui_executor import build_ui_url
from ..services.ui_recorder import RecorderSession, recorder_manager
from ..utils import fmt_time


router = APIRouter(prefix="/ui-recorder", tags=["ui-recorder"])


class UiRecorderSessionIn(BaseModel):
    environment_id: int
    start_url: str


def _session_out(session: RecorderSession) -> dict:
    return {
        "id": session.id,
        "status": session.status,
        "message": session.message,
        "result": session.result,
        "error": session.error,
        "create_date": fmt_time(session.created_at),
        "update_date": fmt_time(session.updated_at),
    }


@router.post("/sessions")
def create_recorder_session(payload: UiRecorderSessionIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    environment = db.get(Environment, payload.environment_id)
    if not environment or environment.is_deleted:
        raise HTTPException(status_code=404, detail="环境不存在")
    if not payload.start_url.strip():
        raise HTTPException(status_code=400, detail="请先填写目标地址")
    url = build_ui_url(environment, payload.start_url)
    session = recorder_manager.create_session(url)
    log_operation(db, user, "ui", "record", "started ui element picker")
    return _session_out(session)


@router.get("/sessions/{session_id}")
def get_recorder_session(session_id: str, _: User = Depends(current_user)):
    session = recorder_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="拾取会话不存在或已过期")
    return _session_out(session)


@router.post("/sessions/{session_id}/close")
def close_recorder_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = recorder_manager.close_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="拾取会话不存在或已过期")
    log_operation(db, user, "ui", "record_close", "closed ui element picker")
    return _session_out(session)
