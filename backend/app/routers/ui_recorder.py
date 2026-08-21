from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Environment, User
from ..services.operation_logs import log_operation
from ..services.ui_executor import build_ui_url
from ..services.ui_recorder import VIEWPORT, RecorderSession, recorder_manager
from ..utils import fmt_time


router = APIRouter(prefix="/ui-recorder", tags=["ui-recorder"])


class UiRecorderSessionIn(BaseModel):
    environment_id: int
    start_url: str


class UiRecorderPointIn(BaseModel):
    x: float
    y: float


class UiRecorderTypeIn(BaseModel):
    text: str


class UiRecorderPressIn(BaseModel):
    key: str = "Enter"


class UiRecorderSelectIn(BaseModel):
    xpath: str
    value: str
    label: str = ""


def _session_out(session: RecorderSession) -> dict:
    return {
        "id": session.id,
        "status": session.status,
        "message": session.message,
        "result": session.result,
        "error": session.error,
        "viewport": VIEWPORT,
        "create_date": fmt_time(session.created_at),
        "update_date": fmt_time(session.updated_at),
    }


def _session_or_404(session_id: str) -> RecorderSession:
    session = recorder_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="拾取会话不存在或已过期")
    return session


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
    return _session_out(_session_or_404(session_id))


@router.get("/sessions/{session_id}/screenshot")
def get_recorder_screenshot(session_id: str, _: User = Depends(current_user)):
    session = _session_or_404(session_id)
    try:
        image = recorder_manager.run_command(session, "screenshot", timeout=10)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=image, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/sessions/{session_id}/click")
def click_recorder_session(session_id: str, payload: UiRecorderPointIn, _: User = Depends(current_user)):
    session = _session_or_404(session_id)
    try:
        recorder_manager.run_command(session, "click", payload.model_dump(), timeout=10)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _session_out(session)


@router.post("/sessions/{session_id}/pick")
def pick_recorder_session(session_id: str, payload: UiRecorderPointIn, _: User = Depends(current_user)):
    session = _session_or_404(session_id)
    try:
        recorder_manager.run_command(session, "pick", payload.model_dump(), timeout=10)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _session_out(session)


@router.post("/sessions/{session_id}/type")
def type_recorder_session(session_id: str, payload: UiRecorderTypeIn, _: User = Depends(current_user)):
    session = _session_or_404(session_id)
    try:
        recorder_manager.run_command(session, "type", payload.model_dump(), timeout=10)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _session_out(session)


@router.post("/sessions/{session_id}/press")
def press_recorder_session(session_id: str, payload: UiRecorderPressIn, _: User = Depends(current_user)):
    session = _session_or_404(session_id)
    try:
        recorder_manager.run_command(session, "press", payload.model_dump(), timeout=10)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _session_out(session)


@router.post("/sessions/{session_id}/select")
def select_recorder_session(session_id: str, payload: UiRecorderSelectIn, _: User = Depends(current_user)):
    session = _session_or_404(session_id)
    try:
        recorder_manager.run_command(session, "select", payload.model_dump(), timeout=10)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _session_out(session)


@router.post("/sessions/{session_id}/close")
def close_recorder_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = recorder_manager.close_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="拾取会话不存在或已过期")
    log_operation(db, user, "ui", "record_close", "closed ui element picker")
    return _session_out(session)
