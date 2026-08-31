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


class MockEndpointIn(BaseModel):
    project_id: int
    environment_id: int
    name: str
    method: HttpMethod
    path: str
    status: Literal["active", "disabled"] = "active"
    status_code: int = 200
    delay_ms: int = 0
    headers: dict[str, Any] = {}
    response_body: str = ""
    body_format: Literal["json", "xml", "text"] = "json"
    sm3_enabled: bool = False
    description: str = ""


class MockEndpointUpdate(MockEndpointIn):
    pass


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
    sm3_signature: bool = False


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
    grant_type: str = "client_credentials"
    client_id: str = ""
    client_secret: str = ""
    scope: str = ""
    audience: str = ""
    client_authentication: Literal["body", "basic"] = "body"
    verify_tls: bool = True


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
    target_type: Literal["case", "scenario", "plan", "ui_case"]
    target_id: int


class UiStepIn(BaseModel):
    action: Literal["goto", "click", "dblclick", "fill", "select", "wait", "assert_text", "assert_visible", "screenshot"]
    locator_type: Literal["text", "css", "xpath", "placeholder", "role", "ai"] = "css"
    target: str = ""
    value: str = ""
    description: str = ""


class UiTestCaseIn(BaseModel):
    project_id: int
    environment_id: int
    name: str
    start_url: str = ""
    description: str = ""
    execution_mode: Literal["ai", "advanced"] = "advanced"
    test_goal: str = ""
    test_data: dict[str, Any] = {}
    assertion_goal: str = ""
    max_steps: int = 30
    step_timeout_ms: int = 10000
    allow_ai_actions: bool = True
    status: Literal["active", "disabled"] = "active"
    browser_channel: Literal["chromium", "chrome", "msedge"] = "chromium"
    headless: bool = True
    wait_until: Literal["domcontentloaded", "load", "networkidle"] = "networkidle"
    wait_after_load_ms: int = 500
    steps: list[UiStepIn] = []


class UiTestCaseUpdate(UiTestCaseIn):
    pass


class UiGenerateStepsIn(BaseModel):
    prompt: str
    start_url: str = ""
    existing_steps: list[UiStepIn] = []


class AiSettingIn(BaseModel):
    id: int | None = None
    name: str = ""
    provider_url: str = ""
    model_name: str = ""
    api_key: str = ""
    status: Literal["active", "disabled"] = "disabled"
    is_default: bool = False
    description: str = ""


class KnowledgeBaseIn(BaseModel):
    project_id: int
    name: str
    dify_dataset_id: str
    status: Literal["active", "disabled"] = "active"
    description: str = ""


class KnowledgeBaseUpdate(BaseModel):
    project_id: int
    name: str
    dify_dataset_id: str
    status: Literal["active", "disabled"] = "active"
    description: str = ""


class KnowledgeRetrieveIn(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=10)
    score_threshold: float | None = Field(default=None, ge=0, le=1)


class KnowledgeCheckIn(BaseModel):
    dify_dataset_id: str


class ApiKeyConfigIn(BaseModel):
    env_key: str
    display_name: str
    status: Literal["active", "disabled"] = "active"
    description: str = ""


class ApiKeyConfigUpdate(BaseModel):
    env_key: str
    display_name: str
    status: Literal["active", "disabled"] = "active"
    description: str = ""


class KnowledgeProjectIn(BaseModel):
    name: str
    description: str = ""
    status: Literal["active", "disabled"] = "active"


class KnowledgeProjectUpdate(BaseModel):
    name: str
    description: str = ""
    status: Literal["active", "disabled"] = "active"


class KnowledgeWorkflowIn(BaseModel):
    name: str
    api_base_url: str = ""
    api_key_env: str
    status: Literal["active", "disabled"] = "active"
    description: str = ""


class KnowledgeWorkflowUpdate(BaseModel):
    name: str
    api_base_url: str = ""
    api_key_env: str = ""
    status: Literal["active", "disabled"] = "active"
    description: str = ""


class KnowledgeQaSessionIn(BaseModel):
    project_id: int
    workflow_id: int
    title: str = ""


class KnowledgeQaSessionUpdate(BaseModel):
    title: str


class KnowledgeQaAskIn(BaseModel):
    question: str


class TicketProcessIn(BaseModel):
    status: Literal["processing", "resolved"]
    reply: str = Field(max_length=5000)
