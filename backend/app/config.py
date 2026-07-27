from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="mysql+pymysql://api_test:api_test@localhost:3306/api_test_platform?charset=utf8mb4")
    app_secret: str = Field(default="dev-secret")
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="admin123")
    response_body_limit: int = Field(default=65535)
    queue_poll_interval_seconds: float = Field(default=1.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
