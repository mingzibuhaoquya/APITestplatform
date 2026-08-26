from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class TimestampMixin:
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class User(Base, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    real_name: Mapped[str] = mapped_column(String(64), default="")
    role: Mapped[str] = mapped_column(String(32), default="tester")
    status: Mapped[str] = mapped_column(String(32), default="active")
    last_login_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Role(Base, TimestampMixin):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    menus_json: Mapped[str] = mapped_column(Text, default="[]")


class Project(Base, TimestampMixin):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active")
    creator_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)


class Environment(Base, TimestampMixin):
    __tablename__ = "environment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(128))
    base_url: Mapped[str] = mapped_column(String(512))
    protocol: Mapped[str] = mapped_column(String(16), default="https", server_default="https")
    port: Mapped[int] = mapped_column(Integer, default=443, server_default="443")
    headers_json: Mapped[str] = mapped_column(Text, default="{}")
    variables_json: Mapped[str] = mapped_column(Text, default="{}")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)


class ApiDefinition(Base, TimestampMixin):
    __tablename__ = "api_definition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    environment_id: Mapped[int] = mapped_column(Integer, default=0, server_default="0", index=True)
    module: Mapped[str] = mapped_column(String(128), default="")
    name: Mapped[str] = mapped_column(String(128))
    method: Mapped[str] = mapped_column(String(16))
    path: Mapped[str] = mapped_column(String(512))
    headers_json: Mapped[str] = mapped_column(Text, default="{}")
    query_json: Mapped[str] = mapped_column(Text, default="{}")
    body_json: Mapped[str] = mapped_column(Text, default="{}")
    description: Mapped[str] = mapped_column(Text, default="")
    pre_script: Mapped[str] = mapped_column(Text, default="")
    encryption_config_json: Mapped[str] = mapped_column(Text, default="{}")
    auth_config_json: Mapped[str] = mapped_column(Text, default="{}")


class MockEndpoint(Base, TimestampMixin):
    __tablename__ = "mock_endpoint"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    environment_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(128))
    method: Mapped[str] = mapped_column(String(16))
    path: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="active")
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    delay_ms: Mapped[int] = mapped_column(Integer, default=0)
    headers_json: Mapped[str] = mapped_column(Text, default="{}")
    response_body: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"), default="")
    body_format: Mapped[str] = mapped_column(String(32), default="json")
    sm3_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)


class TestCase(Base, TimestampMixin):
    __tablename__ = "test_case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    api_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(128))
    request_headers_json: Mapped[str] = mapped_column(Text, default="{}")
    request_query_json: Mapped[str] = mapped_column(Text, default="{}")
    request_body_json: Mapped[str] = mapped_column(Text, default="{}")
    assertions_json: Mapped[str] = mapped_column(Text, default="[]")
    extractors_json: Mapped[str] = mapped_column(Text, default="[]")
    tags: Mapped[str] = mapped_column(String(255), default="")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    maintainer_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class ScenarioCase(Base, TimestampMixin):
    __tablename__ = "scenario_case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(128))
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    failure_strategy: Mapped[str] = mapped_column(String(32), default="stop")
    status: Mapped[str] = mapped_column(String(32), default="active")


class TestSuite(Base, TimestampMixin):
    __tablename__ = "test_suite"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    environment_id: Mapped[int] = mapped_column(Integer, default=0, server_default="0", index=True)
    api_id: Mapped[int] = mapped_column(Integer, default=0, server_default="0", index=True)
    creator_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    items_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(32), default="active")
    last_execution_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    last_status: Mapped[str] = mapped_column(String(32), default="")
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)


class ExecutionTask(Base, TimestampMixin):
    __tablename__ = "execution_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    executor_id: Mapped[int] = mapped_column(Integer, index=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    environment_id: Mapped[int] = mapped_column(Integer, index=True)
    target_type: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    report_html: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"), default="")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)


class ExecutionResult(Base, TimestampMixin):
    __tablename__ = "execution_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, index=True)
    case_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32))
    request_snapshot_json: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"), default="{}")
    response_snapshot_json: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"), default="{}")
    assertion_results_json: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"), default="[]")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"), default="")


class UiTestCase(Base, TimestampMixin):
    __tablename__ = "ui_test_case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    environment_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(128))
    start_url: Mapped[str] = mapped_column(String(1024), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    execution_mode: Mapped[str] = mapped_column(String(32), default="advanced", server_default="advanced")
    test_goal: Mapped[str] = mapped_column(Text, default="")
    test_data_json: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"), default="{}")
    assertion_goal: Mapped[str] = mapped_column(Text, default="")
    max_steps: Mapped[int] = mapped_column(Integer, default=30, server_default="30")
    step_timeout_ms: Mapped[int] = mapped_column(Integer, default=10000, server_default="10000")
    allow_ai_actions: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    steps_json: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"), default="[]")
    status: Mapped[str] = mapped_column(String(32), default="active")
    headless: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    wait_until: Mapped[str] = mapped_column(String(32), default="networkidle")
    wait_after_load_ms: Mapped[int] = mapped_column(Integer, default=500)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    maintainer_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class UiExecutionArtifact(Base, TimestampMixin):
    __tablename__ = "ui_execution_artifact"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, index=True)
    result_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    artifact_type: Mapped[str] = mapped_column(String(32), default="screenshot")
    file_path: Mapped[str] = mapped_column(String(1024), default="")


class AiSetting(Base, TimestampMixin):
    __tablename__ = "ai_setting"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_url: Mapped[str] = mapped_column(String(1024), default="")
    model_name: Mapped[str] = mapped_column(String(128), default="")
    api_key: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="disabled")
    description: Mapped[str] = mapped_column(Text, default="")


class OperationLog(Base, TimestampMixin):
    __tablename__ = "operation_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(String(32), default="success")
    ip: Mapped[str] = mapped_column(String(64), default="")
