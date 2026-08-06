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
    role: str = "tester"


class UserUpdate(BaseModel):
    username: str
    real_name: str
    role: str = "tester"


class UserStatusUpdate(BaseModel):
    status: Literal["active", "disabled"]


class UserOut(BaseModel):
    id: int
    username: str
    real_name: str
    role: str
    role_name: str = ""
    menus: list[str] = []
    status: str
    create_date: str | None
    update_date: str | None


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class RoleIn(BaseModel):
    code: str
    name: str
    description: str = ""
    status: Literal["active", "disabled"] = "active"
    menus: list[str] = []


class RoleUpdate(BaseModel):
    name: str
    description: str = ""
    status: Literal["active", "disabled"] = "active"
    menus: list[str] = []


class RoleOut(BaseModel):
    id: int
    code: str
    name: str
    description: str
    status: str
    is_builtin: bool
    menus: list[str]
    user_count: int = 0
    create_date: str | None
    update_date: str | None


class RoleListOut(BaseModel):
    items: list[RoleOut]
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


class EncryptionConfigIn(BaseModel):
    mode: Literal["none", "rsa_aes_sm3"] = "none"
    encrypt_request: bool = False
    decrypt_response: bool = False
    client_header: str = "appKey"


class AuthConfigIn(BaseModel):
    type: Literal["none", "bearer", "basic", "api_key", "oauth2_client_credentials"] = "none"
    add_to: Literal["headers", "query"] = "headers"
    header_name: str = "Authorization"
    header_prefix: str = "Bearer"
    token: str = ""
    username: str = ""
    password: str = ""
    api_key_name: str = ""
    api_key_value: str = ""
    token_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    scope: str = ""
    audience: str = ""
    client_authentication: Literal["body", "basic"] = "body"


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
    pre_script: str = ""
    encryption: EncryptionConfigIn | None = None
    auth: AuthConfigIn | None = None


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
    pre_script: str = ""
    encryption: EncryptionConfigIn | None = None
    auth: AuthConfigIn | None = None


class AuthTokenPreviewIn(BaseModel):
    environment_id: int = 0
    path: str = ""
    auth: AuthConfigIn


class AssertionRule(BaseModel):
    type: Literal[
        "status_code",
        "jsonpath_equal",
        "jsonpath_exists",
        "jsonpath_not_empty",
        "xmlpath_equal",
        "xmlpath_exists",
        "xmlpath_not_empty",
        "duration_lt",
        "body_contains",
    ]
    path: str = ""
    expected: Any = None


class ExtractorRule(BaseModel):
    name: str
    path: str
    source: Literal["jsonpath", "xmlpath", "regex"] = "jsonpath"


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
    items: list[int | dict[str, Any]]


class TestPlanUpdate(BaseModel):
    project_id: int
    environment_id: int
    api_id: int
    name: str
    items: list[int | dict[str, Any]]


class ExecutionCreate(BaseModel):
    project_id: int
    environment_id: int
    target_type: Literal["case", "scenario", "plan"]
    target_id: int
