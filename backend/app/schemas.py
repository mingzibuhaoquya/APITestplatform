from typing import Any, Literal
from pydantic import BaseModel, Field


Role = Literal["admin", "tester"]
HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


class LoginIn(BaseModel):
    username: str
    password: str


class MockUserLoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


class UserCreate(BaseModel):
    username: str
    password: str = Field(min_length=6)
    real_name: str = ""
    role: Role = "tester"


class UserUpdate(BaseModel):
    username: str
    real_name: str


class UserStatusUpdate(BaseModel):
    status: Literal["active", "disabled"]


class UserOut(BaseModel):
    id: int
    username: str
    real_name: str
    role: str
    status: str
    create_date: str | None
    update_date: str | None


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class ProjectIn(BaseModel):
    name: str
    description: str = ""
    status: str = "active"


class ProjectUpdate(BaseModel):
    name: str
    description: str = ""


class EnvironmentIn(BaseModel):
    project_id: int
    name: str
    protocol: Literal["http", "https"]
    base_url: str
    port: int | None = None
    headers: dict[str, Any] = {}
    variables: dict[str, Any] = {}


class EnvironmentUpdate(BaseModel):
    project_id: int
    name: str
    protocol: Literal["http", "https"]
    base_url: str
    port: int | None = None


class ApiDefinitionIn(BaseModel):
    project_id: int
    environment_id: int = 0
    module: str = ""
    name: str
    method: HttpMethod
    path: str
    headers: dict[str, Any] = {}
    query: dict[str, Any] = {}
    body: Any = {}
    description: str = ""


class ApiDefinitionUpdate(BaseModel):
    project_id: int
    environment_id: int = 0
    name: str
    method: HttpMethod
    path: str
    headers: dict[str, Any] = {}
    query: dict[str, Any] = {}
    body: Any = {}
    description: str = ""


class AssertionRule(BaseModel):
    type: Literal["status_code", "jsonpath_equal", "jsonpath_exists", "jsonpath_not_empty", "duration_lt", "body_contains"]
    path: str = ""
    operator: str = "=="
    expected: Any = None


class ExtractorRule(BaseModel):
    name: str
    path: str


class TestCaseIn(BaseModel):
    project_id: int
    api_id: int
    name: str
    request_headers: dict[str, Any] = {}
    request_query: dict[str, Any] = {}
    request_body: Any = {}
    assertions: list[AssertionRule] = []
    extractors: list[ExtractorRule] = []
    tags: str = ""
    priority: str = "P2"


class TestCaseUpdate(BaseModel):
    project_id: int
    api_id: int
    name: str
    request_headers: dict[str, Any] = {}
    request_query: dict[str, Any] = {}
    request_body: Any = {}
    assertions: list[AssertionRule] = []
    extractors: list[ExtractorRule] = []
    tags: str = ""
    priority: str = "P2"


class ScenarioCaseIn(BaseModel):
    project_id: int
    name: str
    steps: list[int]
    failure_strategy: Literal["stop", "continue"] = "stop"
    status: str = "active"


class TestPlanIn(BaseModel):
    project_id: int
    environment_id: int
    api_id: int
    name: str
    items: list[int]


class TestPlanUpdate(BaseModel):
    project_id: int
    environment_id: int
    api_id: int
    name: str
    items: list[int]


class ExecutionCreate(BaseModel):
    project_id: int
    environment_id: int
    target_type: Literal["case", "scenario", "plan"]
    target_id: int
