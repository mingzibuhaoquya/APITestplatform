import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import current_user
from ..models import AiCaseGeneration, User
from ..services.ai_case_generations import DifyGenerationError, generation_files, upload_source_document
from ..services.operation_logs import log_operation
from ..utils import fmt_time


router = APIRouter(prefix="/ai-case-generations", tags=["ai-case-generations"])


def _out(row: AiCaseGeneration, db: Session) -> dict:
    creator = db.get(User, row.creator_id)
    return {
        "id": row.id,
        "source_filename": row.source_filename,
        "status": row.status,
        "workflow_run_id": row.workflow_run_id,
        "output_files": generation_files(row),
        "error_message": row.error_message,
        "creator_name": creator.real_name or creator.username if creator else "",
        "started_at": fmt_time(row.started_at),
        "ended_at": fmt_time(row.ended_at),
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


@router.post("", status_code=201)
async def create_generation(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    filename = Path(file.filename or "").name.strip()
    if not filename:
        raise HTTPException(status_code=400, detail="请选择需求文档")
    content = await file.read()
    if len(content) > get_settings().ai_generation_upload_limit_bytes:
        raise HTTPException(status_code=400, detail="需求文档不能超过 20MB")
    try:
        dify_file_id = await upload_source_document(filename, content, file.content_type or "", user.id)
    except DifyGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    row = AiCaseGeneration(creator_id=user.id, source_filename=filename, dify_file_id=dify_file_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    log_operation(db, user, "ai_case_generation", "create", f"created AI generation {row.id}: {filename}")
    return _out(row, db)


@router.get("")
def list_generations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=20),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(AiCaseGeneration)
    total = query.count()
    rows = query.order_by(AiCaseGeneration.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_out(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/{generation_id}")
def get_generation(generation_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(AiCaseGeneration, generation_id)
    if not row:
        raise HTTPException(status_code=404, detail="生成历史不存在")
    return _out(row, db)


@router.get("/{generation_id}/files/{file_index}")
def download_generation_file(generation_id: int, file_index: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(AiCaseGeneration, generation_id)
    files = generation_files(row) if row else []
    if file_index < 0 or file_index >= len(files):
        raise HTTPException(status_code=404, detail="生成文件不存在")
    item = files[file_index]
    storage_name = Path(str(item.get("storage_name") or "")).name
    path = Path(get_settings().ai_generation_storage_dir) / storage_name
    if not storage_name or not path.is_file():
        raise HTTPException(status_code=404, detail="生成文件已不存在")
    return FileResponse(path, filename=str(item.get("name") or storage_name), media_type=str(item.get("content_type") or mimetypes.guess_type(storage_name)[0] or "application/octet-stream"))


@router.delete("/{generation_id}")
def delete_generation(generation_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(AiCaseGeneration, generation_id)
    if not row:
        raise HTTPException(status_code=404, detail="生成历史不存在")
    for item in generation_files(row):
        storage_name = Path(str(item.get("storage_name") or "")).name
        if storage_name:
            (Path(get_settings().ai_generation_storage_dir) / storage_name).unlink(missing_ok=True)
    db.delete(row)
    db.commit()
    log_operation(db, user, "ai_case_generation", "delete", f"deleted AI generation {generation_id}")
    return {"ok": True}
