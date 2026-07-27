from typing import Any, Literal
from pydantic import BaseModel, Field


Role = Literal["admin", "tester"]
HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


class LoginIn(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str = Field(min_length=6)
    real_name: str = ""
    role: Role = "tester"


class UserOut(BaseModel):
    id: int
    username: str
    real_name: str
    role: str
    status: str
    create_date: str | None
    update_date: str | None


class ProjectIn(BaseModel):
    name: str
    description: str = ""
    status: str = "active"


class EnvironmentIn(BaseModel):
    project_id: int
    name: str
    base_url: str
    headers: dict[str, Any] = {}
    variables: dict[str, Any] = {}


class ApiDefinitionIn(BaseModel):
    project_id: int
    module: str = ""
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
    status: str = "active"


class ScenarioCaseIn(BaseModel):
    project_id: int
    name: str
    steps: list[int]
    failure_strategy: Literal["stop", "continue"] = "stop"
    status: str = "active"


class ExecutionCreate(BaseModel):
    project_id: int
    environment_id: int
    target_type: Literal["case", "scenario"]
    target_id: int

