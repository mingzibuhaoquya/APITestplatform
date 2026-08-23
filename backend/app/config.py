from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="mysql+pymysql://root:root@localhost:3306/apitest?charset=utf8mb4")
    app_secret: str = Field(default="dev-secret")
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="admin123")
    session_idle_timeout_minutes: int = Field(default=30, ge=1)
    session_absolute_timeout_hours: int = Field(default=8, ge=1)
    session_cookie_secure: bool = Field(default=False)
    response_body_limit: int = Field(default=30000)
    queue_poll_interval_seconds: float = Field(default=1.0)
    dify_api_base_url: str = Field(default="http://host.docker.internal:8080/v1")
    dify_workflow_api_key: str = Field(default="")
    dify_knowledge_api_key: str = Field(default="")
    ai_generation_storage_dir: str = Field(default="/app/data/ai-generations")
    ai_generation_upload_limit_bytes: int = Field(default=20 * 1024 * 1024)
    ticket_attachment_storage_dir: str = Field(default="/app/data/ticket-attachments")
    ticket_attachment_limit_bytes: int = Field(default=20 * 1024 * 1024)


@lru_cache
def get_settings() -> Settings:
    return Settings()
