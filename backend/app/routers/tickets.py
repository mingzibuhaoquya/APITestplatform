from datetime import datetime
import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import current_user
from ..models import Ticket, TicketAttachment, User
from ..schemas import TicketProcessIn
from ..services.operation_logs import log_operation
from ..utils import fmt_time

router = APIRouter(prefix="/tickets", tags=["tickets"])
_CATEGORIES = {"feature", "issue", "experience", "other"}

def _attachment_out(row: TicketAttachment) -> dict:
    return {"id": row.id, "name": row.original_name, "content_type": row.content_type, "size": row.size}

def _out(row: Ticket, db: Session, detail: bool = False) -> dict:
    submitter, handler = db.get(User, row.submitter_id), db.get(User, row.handler_id) if row.handler_id else None
    result = {"id": row.id, "category": row.category, "title": row.title, "status": row.status, "submitter_name": (submitter.real_name or submitter.username) if submitter else "", "handler_name": (handler.real_name or handler.username) if handler else "", "handled_at": fmt_time(row.handled_at), "create_date": fmt_time(row.create_date), "update_date": fmt_time(row.update_date)}
    if detail:
        result.update({"content": row.content, "reply": row.reply, "attachments": [_attachment_out(item) for item in db.query(TicketAttachment).filter(TicketAttachment.ticket_id == row.id).order_by(TicketAttachment.id).all()]})
    return result

def _require_admin(user: User) -> None:
    if user.role != "admin": raise HTTPException(status_code=403, detail="仅管理员可以处理工单")

@router.post("", status_code=201)
async def create_ticket(category: str = Form(...), title: str = Form(...), content: str = Form(...), files: list[UploadFile] = File(default=[]), user: User = Depends(current_user), db: Session = Depends(get_db)):
    category, title, content = category.strip(), title.strip(), content.strip()
    if category not in _CATEGORIES: raise HTTPException(status_code=400, detail="工单类型无效")
    if not title or len(title) > 200: raise HTTPException(status_code=400, detail="工单标题不能为空且不能超过 200 字")
    if not content or len(content) > 5000: raise HTTPException(status_code=400, detail="建议内容不能为空且不能超过 5000 字")
    if len(files) > 5: raise HTTPException(status_code=400, detail="每张工单最多上传 5 个附件")
    storage, payloads = Path(get_settings().ticket_attachment_storage_dir), []
    storage.mkdir(parents=True, exist_ok=True)
    for file in files:
        name, data = Path(file.filename or "").name.strip(), await file.read()
        if not name: raise HTTPException(status_code=400, detail="附件文件名不能为空")
        if len(data) > get_settings().ticket_attachment_limit_bytes: raise HTTPException(status_code=400, detail="单个附件不能超过 20MB")
        payloads.append((name, file.content_type or "", data))
    row = Ticket(submitter_id=user.id, category=category, title=title, content=content)
    db.add(row); db.flush(); saved = []
    try:
        for name, content_type, data in payloads:
            storage_name, path = f"{uuid4().hex}_{name}", None
            path = storage / storage_name; path.write_bytes(data); saved.append(path)
            db.add(TicketAttachment(ticket_id=row.id, original_name=name, storage_name=storage_name, content_type=content_type, size=len(data)))
        db.commit()
    except Exception:
        db.rollback()
        for path in saved: path.unlink(missing_ok=True)
        raise
    db.refresh(row); log_operation(db, user, "ticket", "create", f"submitted ticket {row.id}: {row.title}")
    return _out(row, db, True)

@router.get("")
def list_tickets(title: str = "", category: str = "", status: str = "", page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=20), _: User = Depends(current_user), db: Session = Depends(get_db)):
    query = db.query(Ticket)
    if title.strip(): query = query.filter(Ticket.title.like(f"%{title.strip()}%"))
    if category.strip(): query = query.filter(Ticket.category == category.strip())
    if status.strip(): query = query.filter(Ticket.status == status.strip())
    total = query.count(); rows = query.order_by(Ticket.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_out(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}

@router.get("/{ticket_id}")
def get_ticket(ticket_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Ticket, ticket_id)
    if not row: raise HTTPException(status_code=404, detail="工单不存在")
    return _out(row, db, True)

@router.put("/{ticket_id}/process")
def process_ticket(ticket_id: int, payload: TicketProcessIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_admin(user); row = db.get(Ticket, ticket_id)
    if not row: raise HTTPException(status_code=404, detail="工单不存在")
    reply = payload.reply.strip()
    if payload.status == "resolved" and not reply: raise HTTPException(status_code=400, detail="标记已解决时必须填写处理回复")
    row.status, row.reply, row.handler_id, row.handled_at = payload.status, reply, user.id, datetime.now()
    db.commit(); db.refresh(row); log_operation(db, user, "ticket", "process", f"processed ticket {row.id}: {row.status}")
    return _out(row, db, True)

@router.get("/{ticket_id}/attachments/{attachment_id}")
def download_attachment(ticket_id: int, attachment_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(TicketAttachment, attachment_id)
    if not item or item.ticket_id != ticket_id: raise HTTPException(status_code=404, detail="附件不存在")
    path = Path(get_settings().ticket_attachment_storage_dir) / Path(item.storage_name).name
    if not path.is_file(): raise HTTPException(status_code=404, detail="附件文件已不存在")
    return FileResponse(path, filename=item.original_name, media_type=item.content_type or mimetypes.guess_type(item.original_name)[0] or "application/octet-stream")
