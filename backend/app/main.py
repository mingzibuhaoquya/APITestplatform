import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from .config import get_settings
from .database import Base, SessionLocal, engine
from .models import TestCase, User
from .routers import auth, crud, executions, mock, roles, ui, users
from .security import hash_password
from .services.menus import ensure_default_roles
from .services.operation_logs import log_system_exception
from .utils import dump_json, parse_json


os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="接口自动化测试平台", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(crud.router)
app.include_router(executions.router)
app.include_router(mock.router)
app.include_router(ui.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.exception("Unhandled system exception: %s %s", request.method, request.url.path)
    db = SessionLocal()
    try:
        log_system_exception(
            db,
            method=request.method,
            path=request.url.path,
            error_type=exc.__class__.__name__,
            message=str(exc),
            ip=request.client.host if request.client else "",
        )
    except Exception:
        logging.exception("Unable to persist system exception log")
    finally:
        db.close()
    return JSONResponse(status_code=500, content={"detail": "系统异常，请查看异常日志"})


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_project_deleted_column()
    _ensure_environment_deleted_column()
    _ensure_api_definition_columns()
    _ensure_test_case_columns()
    _remove_test_case_assertion_operators()
    _ensure_test_suite_columns()
    _ensure_execution_task_columns()
    _ensure_execution_result_columns()
    _ensure_ui_test_case_columns()
    _ensure_ai_setting_columns()
    _ensure_mock_endpoint_columns()
    _ensure_roles()
    _ensure_admin()


def _ensure_project_deleted_column() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("project")}
    if "is_deleted" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE project ADD COLUMN is_deleted BOOL NOT NULL DEFAULT 0"))


def _ensure_environment_deleted_column() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("environment")}
    with engine.begin() as conn:
        if "is_deleted" not in columns:
            conn.execute(text("ALTER TABLE environment ADD COLUMN is_deleted BOOL NOT NULL DEFAULT 0"))
        if "protocol" not in columns:
            conn.execute(text("ALTER TABLE environment ADD COLUMN protocol VARCHAR(16) NOT NULL DEFAULT 'https'"))
        if "port" not in columns:
            conn.execute(text("ALTER TABLE environment ADD COLUMN port INT NOT NULL DEFAULT 443"))


def _ensure_api_definition_columns() -> None:
    inspector = inspect(engine)
    ordered_columns = [column["name"] for column in inspector.get_columns("api_definition")]
    columns = set(ordered_columns)
    with engine.begin() as conn:
        if "environment_id" not in columns:
            conn.execute(text("ALTER TABLE api_definition ADD COLUMN environment_id INT NOT NULL DEFAULT 0 AFTER description"))
        elif ordered_columns.index("environment_id") > ordered_columns.index("create_date"):
            conn.execute(text("ALTER TABLE api_definition MODIFY COLUMN environment_id INT NOT NULL DEFAULT 0 AFTER description"))
        if "pre_script" not in columns:
            conn.execute(text("ALTER TABLE api_definition ADD COLUMN pre_script TEXT NOT NULL AFTER environment_id"))
        if "encryption_config_json" not in columns:
            conn.execute(text("ALTER TABLE api_definition ADD COLUMN encryption_config_json TEXT NOT NULL AFTER pre_script"))
        if "auth_config_json" not in columns:
            conn.execute(text("ALTER TABLE api_definition ADD COLUMN auth_config_json TEXT NOT NULL AFTER encryption_config_json"))


def _ensure_test_case_columns() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("test_case")}
    with engine.begin() as conn:
        if "is_deleted" not in columns:
            conn.execute(text("ALTER TABLE test_case ADD COLUMN is_deleted BOOL NOT NULL DEFAULT 0"))
        if "status" in columns:
            conn.execute(text("ALTER TABLE test_case DROP COLUMN status"))
        if "priority" in columns:
            conn.execute(text("ALTER TABLE test_case DROP COLUMN priority"))


def _without_assertion_operators(assertions: object) -> object:
    if not isinstance(assertions, list):
        return assertions
    return [
        {key: value for key, value in item.items() if key != "operator"} if isinstance(item, dict) else item
        for item in assertions
    ]


def _remove_test_case_assertion_operators() -> None:
    db = SessionLocal()
    try:
        changed = False
        for case in db.query(TestCase).all():
            assertions = parse_json(case.assertions_json, [])
            cleaned = _without_assertion_operators(assertions)
            if cleaned != assertions:
                case.assertions_json = dump_json(cleaned)
                changed = True
        if changed:
            db.commit()
    finally:
        db.close()


def _ensure_test_suite_columns() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("test_suite")}
    with engine.begin() as conn:
        if "environment_id" not in columns:
            conn.execute(text("ALTER TABLE test_suite ADD COLUMN environment_id INT NOT NULL DEFAULT 0"))
        if "api_id" not in columns:
            conn.execute(text("ALTER TABLE test_suite ADD COLUMN api_id INT NOT NULL DEFAULT 0"))
        if "creator_id" not in columns:
            conn.execute(text("ALTER TABLE test_suite ADD COLUMN creator_id INT NULL"))
        if "last_execution_id" not in columns:
            conn.execute(text("ALTER TABLE test_suite ADD COLUMN last_execution_id INT NULL"))
        if "last_status" not in columns:
            conn.execute(text("ALTER TABLE test_suite ADD COLUMN last_status VARCHAR(32) NOT NULL DEFAULT ''"))
        if "last_executed_at" not in columns:
            conn.execute(text("ALTER TABLE test_suite ADD COLUMN last_executed_at DATETIME NULL"))
        if "is_deleted" not in columns:
            conn.execute(text("ALTER TABLE test_suite ADD COLUMN is_deleted BOOL NOT NULL DEFAULT 0"))


def _ensure_execution_task_columns() -> None:
    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("execution_task")}
    with engine.begin() as conn:
        if "is_deleted" not in columns:
            conn.execute(text("ALTER TABLE execution_task ADD COLUMN is_deleted BOOL NOT NULL DEFAULT 0"))
        if engine.dialect.name == "mysql" and "LONGTEXT" not in str(columns["report_html"]["type"]).upper():
            conn.execute(text("ALTER TABLE execution_task MODIFY COLUMN report_html LONGTEXT NOT NULL"))


def _ensure_execution_result_columns() -> None:
    if engine.dialect.name != "mysql":
        return
    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("execution_result")}
    longtext_columns = ["request_snapshot_json", "response_snapshot_json", "assertion_results_json", "error_message"]
    with engine.begin() as conn:
        for column_name in longtext_columns:
            column = columns.get(column_name)
            if column and "LONGTEXT" not in str(column["type"]).upper():
                conn.execute(text(f"ALTER TABLE execution_result MODIFY COLUMN {column_name} LONGTEXT NOT NULL"))


def _ensure_ui_test_case_columns() -> None:
    inspector = inspect(engine)
    if "ui_test_case" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ui_test_case")}
    with engine.begin() as conn:
        if "headless" not in columns:
            conn.execute(text("ALTER TABLE ui_test_case ADD COLUMN headless BOOL NOT NULL DEFAULT 1"))
        if "wait_until" not in columns:
            conn.execute(text("ALTER TABLE ui_test_case ADD COLUMN wait_until VARCHAR(32) NOT NULL DEFAULT 'networkidle'"))
        if "wait_after_load_ms" not in columns:
            conn.execute(text("ALTER TABLE ui_test_case ADD COLUMN wait_after_load_ms INT NOT NULL DEFAULT 500"))


def _ensure_ai_setting_columns() -> None:
    inspector = inspect(engine)
    if "ai_setting" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ai_setting")}
    if "description" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE ai_setting ADD COLUMN description TEXT NOT NULL"))


def _ensure_mock_endpoint_columns() -> None:
    inspector = inspect(engine)
    if "mock_endpoint" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("mock_endpoint")}
    if "sm3_enabled" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE mock_endpoint ADD COLUMN sm3_enabled BOOL NOT NULL DEFAULT 0 AFTER body_format"))


def _ensure_roles() -> None:
    db: Session = SessionLocal()
    try:
        ensure_default_roles(db)
    finally:
        db.close()


def _ensure_admin() -> None:
    settings = get_settings()
    db: Session = SessionLocal()
    try:
        exists = db.query(User).filter(User.username == settings.admin_username).first()
        if not exists:
            db.add(User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                real_name="系统管理员",
                role="admin",
            ))
            db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
