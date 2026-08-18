import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Environment, MockEndpoint, Project, User
from ..schemas import MockEndpointIn, MockEndpointUpdate, MockUserLoginIn
from ..services.crypto_envelope import sm3_hex
from ..services.operation_logs import log_operation
from ..utils import dump_json, fmt_time, parse_json


router = APIRouter(tags=["mock"])


def _normalize_mock_path(path: str) -> str:
    value = path.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Mock 路径不能为空")
    return "/" + value.lstrip("/")


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


def _validate_mock_payload(payload: MockEndpointIn | MockEndpointUpdate, db: Session, mock_id: int | None = None):
    _active_project(payload.project_id, db)
    _active_environment(payload.environment_id, payload.project_id, db)
    name = payload.name.strip()
    path = _normalize_mock_path(payload.path)
    status_code = int(payload.status_code)
    delay_ms = int(payload.delay_ms)
    if not name:
        raise HTTPException(status_code=400, detail="Mock 名称不能为空")
    if status_code < 100 or status_code > 599:
        raise HTTPException(status_code=400, detail="HTTP 状态码必须在 100-599 之间")
    if delay_ms < 0:
        raise HTTPException(status_code=400, detail="延迟时间不能小于 0")
    if payload.status == "active":
        exists = db.query(MockEndpoint).filter(
            MockEndpoint.environment_id == payload.environment_id,
            MockEndpoint.method == payload.method,
            MockEndpoint.path == path,
            MockEndpoint.status == "active",
            MockEndpoint.is_deleted.is_(False),
        )
        if mock_id is not None:
            exists = exists.filter(MockEndpoint.id != mock_id)
        if exists.first():
            raise HTTPException(status_code=400, detail="当前环境下已存在相同方法和路径的启用 Mock")
    return name, path, status_code, delay_ms


def _mock_out(row: MockEndpoint, db: Session):
    project = db.get(Project, row.project_id)
    environment = db.get(Environment, row.environment_id)
    return {
        "id": row.id,
        "project_id": row.project_id,
        "project_name": project.name if project and not project.is_deleted else "",
        "environment_id": row.environment_id,
        "environment_name": environment.name if environment and not environment.is_deleted else "",
        "name": row.name,
        "method": row.method,
        "path": row.path,
        "status": row.status,
        "status_code": row.status_code,
        "delay_ms": row.delay_ms,
        "headers": parse_json(row.headers_json, {}),
        "response_body": row.response_body or "",
        "body_format": row.body_format or "json",
        "sm3_enabled": row.sm3_enabled,
        "description": row.description or "",
        "is_deleted": row.is_deleted,
        "create_date": fmt_time(row.create_date),
        "update_date": fmt_time(row.update_date),
    }


@router.post("/mock/userLogin")
def user_login(payload: MockUserLoginIn):
    if payload.username == "zmn" and payload.password == "123456":
        return {"result": "success"}
    return JSONResponse(status_code=401, content={"result": "failed"})


@router.get("/mocks")
def list_mocks(
    project_id: int | None = None,
    environment_id: int | None = None,
    name: str = "",
    path: str = "",
    status: str = "",
    page: int | None = None,
    page_size: int | None = None,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(MockEndpoint).join(Project, MockEndpoint.project_id == Project.id).filter(
        Project.is_deleted.is_(False),
        MockEndpoint.is_deleted.is_(False),
    )
    if project_id:
        query = query.filter(MockEndpoint.project_id == project_id)
    if environment_id:
        query = query.filter(MockEndpoint.environment_id == environment_id)
    if name.strip():
        query = query.filter(MockEndpoint.name.like(f"%{name.strip()}%"))
    if path.strip():
        query = query.filter(MockEndpoint.path.like(f"%{path.strip()}%"))
    if status.strip():
        query = query.filter(MockEndpoint.status == status.strip())
    if page is None and page_size is None:
        return [_mock_out(row, db) for row in query.order_by(MockEndpoint.id.desc()).all()]
    page = max(page or 1, 1)
    page_size = min(max(page_size or 10, 1), 20)
    total = query.count()
    rows = query.order_by(MockEndpoint.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_mock_out(row, db) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/mocks")
def create_mock(payload: MockEndpointIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name, path, status_code, delay_ms = _validate_mock_payload(payload, db)
    row = MockEndpoint(
        project_id=payload.project_id,
        environment_id=payload.environment_id,
        name=name,
        method=payload.method,
        path=path,
        status=payload.status,
        status_code=status_code,
        delay_ms=delay_ms,
        headers_json=dump_json(payload.headers),
        response_body=payload.response_body,
        body_format=payload.body_format,
        sm3_enabled=payload.sm3_enabled,
        description=payload.description.strip(),
        is_deleted=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_operation(db, user, "mock", "create", f"created mock {row.name}")
    return _mock_out(row, db)


@router.put("/mocks/{mock_id}")
def update_mock(mock_id: int, payload: MockEndpointUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(MockEndpoint, mock_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="Mock 规则不存在")
    name, path, status_code, delay_ms = _validate_mock_payload(payload, db, mock_id=mock_id)
    row.project_id = payload.project_id
    row.environment_id = payload.environment_id
    row.name = name
    row.method = payload.method
    row.path = path
    row.status = payload.status
    row.status_code = status_code
    row.delay_ms = delay_ms
    row.headers_json = dump_json(payload.headers)
    row.response_body = payload.response_body
    row.body_format = payload.body_format
    row.sm3_enabled = payload.sm3_enabled
    row.description = payload.description.strip()
    db.commit()
    db.refresh(row)
    log_operation(db, user, "mock", "update", f"updated mock {row.name}")
    return _mock_out(row, db)


@router.delete("/mocks/{mock_id}")
def delete_mock(mock_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(MockEndpoint, mock_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="Mock 规则不存在")
    row.is_deleted = True
    db.commit()
    db.refresh(row)
    log_operation(db, user, "mock", "delete", f"deleted mock {row.name}")
    return _mock_out(row, db)


@router.api_route("/mock-api/env/{environment_id}/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def serve_mock(environment_id: int, full_path: str, request: Request, db: Session = Depends(get_db)):
    path = _normalize_mock_path(full_path)
    row = db.query(MockEndpoint).filter(
        MockEndpoint.environment_id == environment_id,
        MockEndpoint.method == request.method,
        MockEndpoint.path == path,
        MockEndpoint.status == "active",
        MockEndpoint.is_deleted.is_(False),
    ).first()
    if not row:
        return JSONResponse(status_code=404, content={"detail": "未匹配到 Mock 规则", "method": request.method, "path": path})
    if row.delay_ms > 0:
        await asyncio.sleep(row.delay_ms / 1000)
    headers = {str(key): str(value) for key, value in parse_json(row.headers_json, {}).items() if str(key).strip()}
    content_type = headers.pop("Content-Type", None) or headers.pop("content-type", None)
    if not content_type:
        if row.body_format == "json":
            content_type = "application/json"
        elif row.body_format == "xml":
            content_type = "application/xml"
        else:
            content_type = "text/plain; charset=utf-8"
    content = row.response_body or ""
    if row.sm3_enabled:
        content = content + sm3_hex(content)
    return Response(content=content, status_code=row.status_code, headers=headers, media_type=content_type)
