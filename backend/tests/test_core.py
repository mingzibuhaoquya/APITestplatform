import pytest
from html import escape
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import _without_assertion_operators
from app.models import Environment, ExecutionResult, ExecutionTask, MockEndpoint, Project, Role, TestCase as TestCaseModel, TestSuite, User
from app.routers.auth import change_password, login
from app.routers.crud import create_api, create_case, create_environment, create_plan, create_project, delete_api, delete_case, delete_environment, delete_plan, delete_project, execute_plan, get_execution_log_detail, list_apis, list_cases, list_environments, list_exception_logs, list_execution_logs, list_logs, list_plans, list_projects, update_api, update_case, update_environment, update_plan, update_project
from app.routers.executions import delete_execution, list_executions
from app.routers.mock import create_mock, delete_mock, list_mocks, router as mock_router, update_mock
from app.routers.users import create_user, list_users, router as users_router, update_user, update_user_status
from app.routers.roles import create_role, delete_role, list_roles, update_role
from app.schemas import ApiDefinitionIn, ApiDefinitionUpdate, ChangePasswordIn, EncryptionConfigIn, EnvironmentIn, EnvironmentUpdate, LoginIn, MockEndpointIn, MockEndpointUpdate, ProjectIn, ProjectUpdate, RoleIn, RoleUpdate, TestCaseIn, TestCaseUpdate, TestPlanIn, TestPlanUpdate, UserCreate, UserStatusUpdate, UserUpdate
from app.services.menus import ensure_default_roles
from app.services.assertions import all_passed, run_assertions
from app.services import executor as executor_service
from app.services.executor import _apply_auth_config, _build_request_url, _execute, _initial_variables, _request_oauth2_client_credentials_token
from app.services.jsonpath import find_jsonpath
from app.services.xmlpath import find_xmlpath
from app.services.pre_scripts import PreScriptError, run_pre_script
from app.services.report import build_html_report
from app.services import crypto_envelope
from app.services.operation_logs import log_system_exception
from app.services.variables import render_variables
from app.security import create_session_token, hash_password


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = SessionLocal()
    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        real_name="Admin",
        role="admin",
        status="active",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    try:
        yield db, admin
    finally:
        db.close()


def create_test_environment(project_id: int, admin: User, db):
    return create_environment(
        EnvironmentIn(project_id=project_id, name=f"env_{project_id}", protocol="https", base_url=f"project-{project_id}.example.com"),
        admin,
        db,
    )


def test_render_variables_nested():
    payload = {"headers": {"Authorization": "Bearer ${token}"}, "ids": ["${user_id}"]}
    assert render_variables(payload, {"token": "abc", "user_id": 12}) == {
        "headers": {"Authorization": "Bearer abc"},
        "ids": ["12"],
    }


def test_pre_script_sets_task_variables_and_generates_hashes():
    variables = {"appKey": "secret"}

    logs = run_pre_script(
        """
const reqTime = Date.now();
const content = pm.environment.get('appKey') + reqTime;
pm.environment.set('reqTime', reqTime);
pm.environment.set('appSign', CryptoJS.MD5(content).toString());
pm.environment.set('shaSign', CryptoJS.SHA256(content).toString());
console.info('signature generated', reqTime);
""",
        variables,
    )

    assert variables["reqTime"].isdigit()
    assert len(variables["appSign"]) == 32
    assert len(variables["shaSign"]) == 64
    assert render_variables({"sign": "${appSign}"}, variables)["sign"] == variables["appSign"]
    assert logs == [{"level": "info", "message": f"signature generated {variables['reqTime']}"}]


def test_pre_script_reads_and_updates_request_headers():
    variables = {}
    headers = {"AppSecret": "secret", "appKey": "cms001", "reqTime": "${reqTime}"}

    run_pre_script(
        """
const now = Date.now();
const data = pm.request.headers.get('appsecret') + now + pm.request.headers.get('APPKEY');
pm.request.headers.set('reqTime', now);
pm.request.headers.set('appSign', CryptoJS.MD5(data).toString().toUpperCase());
""",
        variables,
        headers,
    )

    assert headers["reqTime"].isdigit()
    assert len(headers["appSign"]) == 32
    assert "ReqTime" not in headers


def test_rsa_aes_sm3_envelope_round_trip_uses_pem_files(tmp_path, monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_path = tmp_path / "request_public.pem"
    private_path = tmp_path / "response_private.pem"
    public_path.write_bytes(public_pem)
    private_path.write_bytes(private_pem)
    monkeypatch.setattr(crypto_envelope, "FIXED_PUBLIC_KEY_PATH", public_path)
    monkeypatch.setattr(crypto_envelope, "FIXED_PRIVATE_KEY_PATH", private_path)
    config = {"mode": "rsa_aes_sm3", "encrypt_request": True, "decrypt_response": True}

    envelope = crypto_envelope.encrypt_body({"message": "hello", "id": 123}, {"appKey": "flap001"}, config)
    text, decoded = crypto_envelope.decrypt_body(envelope, config)

    assert decoded == {"message": "hello", "id": 123}
    assert text == '{"message":"hello","id":123}'
    assert envelope["client"] == "flap001"
    public = crypto_envelope.public_config(config)
    assert public["public_key_configured"] is True
    assert public["private_key_configured"] is True
    assert "public_key_file" not in public
    assert "private_key_file" not in public


def test_pre_script_failure_does_not_mutate_variables():
    variables = {"token": "original"}

    with pytest.raises(PreScriptError):
        run_pre_script("pm.environment.set('token', 'changed'); throw new Error('broken script');", variables)

    assert variables == {"token": "original"}


def test_pre_script_limits_execution_time():
    with pytest.raises(PreScriptError):
        run_pre_script("while (true) {}", {})


def test_build_request_url_uses_environment_protocol_and_port():
    env = Environment(project_id=1, name="local", protocol="http", base_url="127.0.0.1", port=8080)
    default_https = Environment(project_id=1, name="prod", protocol="https", base_url="api.example.com", port=443)

    assert _build_request_url(env, "/users") == "http://127.0.0.1:8080/users"
    assert _build_request_url(default_https, "v1/users") == "https://api.example.com/v1/users"


def test_initial_variables_add_runtime_unique_values(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="runtime_var_project", description="runtime variables"), admin, db)
    env = create_environment(
        EnvironmentIn(
            project_id=project["id"],
            name="runtime_env",
            protocol="https",
            base_url="runtime.example.com",
            variables={"token": "abc"},
        ),
        admin,
        db,
    )

    variables = _initial_variables(db, env["id"])

    assert variables["token"] == "abc"
    assert variables["unique_username"].startswith("test_user_")
    assert variables["timestamp"]
    assert variables["uuid"]
    assert render_variables({"name": "${unique_username}"}, variables)["name"] == variables["unique_username"]


def test_jsonpath_simple_path_and_index():
    data = {"data": {"users": [{"id": 7}]}}
    assert find_jsonpath(data, "$.data.users[0].id") == [7]


def test_xmlpath_simple_path_and_attribute():
    text = '<TRANSACTION><MESSAGE_BODY><RESPONSE id="r1"><STATUS>0</STATUS></RESPONSE></MESSAGE_BODY></TRANSACTION>'
    assert find_xmlpath(text, "/TRANSACTION/MESSAGE_BODY/RESPONSE/STATUS") == ["0"]
    assert find_xmlpath(text, ".//RESPONSE/@id") == ["r1"]


def test_xmlpath_ignores_trailing_signature_after_xml_document():
    text = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<TRANSACTION><MESSAGE_ESB_HEAD><RET_COMM_STATUS>F</RET_COMM_STATUS></MESSAGE_ESB_HEAD></TRANSACTION>"
        "35674D1491855DF4A44C391AA6DE1A182DE6FF8550189852047EB9433B9365BC"
    )

    assert find_xmlpath(text, "/TRANSACTION/MESSAGE_ESB_HEAD/RET_COMM_STATUS") == ["F"]
    assert find_xmlpath(text, ".//RET_COMM_STATUS") == ["F"]


def test_assertion_rules():
    response = {"status_code": 200, "json": {"code": 0, "data": {"token": "abc"}}, "text": '{"code":0}', "duration_ms": 32}
    results = run_assertions(response, [
        {"type": "status_code", "expected": 200},
        {"type": "jsonpath_equal", "path": "$.code", "expected": 0},
        {"type": "jsonpath_not_empty", "path": "$.data.token"},
        {"type": "duration_lt", "expected": 1000},
        {"type": "body_contains", "expected": "code"},
    ])
    assert all_passed(results)


def test_body_contains_uses_decrypted_text_when_present():
    response = {
        "text": '{"cipher":"encrypted-response"}',
        "decrypted_text": '{"financialProductCode":"PD20260501"}',
    }

    results = run_assertions(response, [{"type": "body_contains", "expected": "financialProductCode"}])

    assert results[0]["passed"] is True
    assert results[0]["actual"] == response["decrypted_text"]


def test_remove_assertion_operator_from_historical_data():
    assertions = [
        {"type": "status_code", "operator": "==", "expected": 200},
        {"type": "jsonpath_exists", "path": "$.data.id"},
    ]

    assert _without_assertion_operators(assertions) == [
        {"type": "status_code", "expected": 200},
        {"type": "jsonpath_exists", "path": "$.data.id"},
    ]


def test_xmlpath_assertion_rules():
    response = {
        "status_code": 200,
        "json": None,
        "text": "<RESPONSE><STATUS>0</STATUS><MESSAGE>ok</MESSAGE></RESPONSE>",
        "duration_ms": 32,
    }
    results = run_assertions(response, [
        {"type": "xmlpath_equal", "path": ".//STATUS", "expected": "0"},
        {"type": "xmlpath_exists", "path": ".//MESSAGE"},
        {"type": "xmlpath_not_empty", "path": ".//MESSAGE"},
    ])
    assert all_passed(results)


def test_numeric_assertion_invalid_expected_fails_without_exception():
    response = {"status_code": 200, "json": {}, "text": "", "duration_ms": 32}
    results = run_assertions(response, [{"type": "status_code", "expected": ""}])
    assert results[0]["passed"] is False
    assert "必须填写数字" in results[0]["message"]


def test_mock_user_login_success():
    app = FastAPI()
    app.include_router(mock_router)
    client = TestClient(app)

    response = client.post("/mock/userLogin", json={"username": "zmn", "password": "123456"})

    assert response.status_code == 200
    assert response.json() == {"result": "success"}


def test_mock_user_login_failed_when_credentials_do_not_match():
    app = FastAPI()
    app.include_router(mock_router)
    client = TestClient(app)

    wrong_password = client.post("/mock/userLogin", json={"username": "zmn", "password": "bad-pass"})
    wrong_username = client.post("/mock/userLogin", json={"username": "bad-user", "password": "123456"})

    assert wrong_password.status_code == 401
    assert wrong_password.json() == {"result": "failed"}
    assert wrong_username.status_code == 401
    assert wrong_username.json() == {"result": "failed"}


def test_mock_user_login_requires_username_and_password():
    app = FastAPI()
    app.include_router(mock_router)
    client = TestClient(app)

    missing_username = client.post("/mock/userLogin", json={"password": "123456"})
    missing_password = client.post("/mock/userLogin", json={"username": "zmn"})

    assert missing_username.status_code == 422
    assert missing_password.status_code == 422


def test_mock_endpoint_crud_and_environment_isolation(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="mock_project", description="mock project"), admin, db)
    first_env = create_environment(EnvironmentIn(project_id=project["id"], name="mock_env_a", protocol="http", base_url="localhost", port=8000), admin, db)
    second_env = create_environment(EnvironmentIn(project_id=project["id"], name="mock_env_b", protocol="http", base_url="localhost", port=8000), admin, db)

    first = create_mock(
        MockEndpointIn(
            project_id=project["id"],
            environment_id=first_env["id"],
            name="合同详情Mock",
            method="POST",
            path="api/contracts/detail",
            status_code=200,
            headers={"Content-Type": "application/json"},
            response_body='{"code":0,"data":{"contractNo":"A001"}}',
            body_format="json",
        ),
        admin,
        db,
    )
    second = create_mock(
        MockEndpointIn(
            project_id=project["id"],
            environment_id=second_env["id"],
            name="合同详情Mock-B",
            method="POST",
            path="/api/contracts/detail",
            status_code=201,
            response_body='{"code":0,"data":{"contractNo":"B001"}}',
            body_format="json",
        ),
        admin,
        db,
    )

    assert first["path"] == "/api/contracts/detail"
    assert second["environment_id"] == second_env["id"]
    assert list_mocks(project_id=project["id"], environment_id=first_env["id"], name="合同", page=1, page_size=10, _=admin, db=db)["total"] == 1

    with pytest.raises(HTTPException) as duplicate_error:
        create_mock(
            MockEndpointIn(
                project_id=project["id"],
                environment_id=first_env["id"],
                name="重复Mock",
                method="POST",
                path="/api/contracts/detail",
            ),
            admin,
            db,
        )
    assert duplicate_error.value.status_code == 400

    updated = update_mock(
        first["id"],
        MockEndpointUpdate(
            project_id=project["id"],
            environment_id=first_env["id"],
            name="合同详情Mock-禁用",
            method="POST",
            path="/api/contracts/detail",
            status="disabled",
            response_body='{"disabled":true}',
        ),
        admin,
        db,
    )
    assert updated["status"] == "disabled"

    deleted = delete_mock(second["id"], admin, db)
    assert deleted["is_deleted"] is True


def test_mock_api_serves_configured_response_without_login(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="mock_runtime_project", description="mock runtime"), admin, db)
    environment = create_environment(EnvironmentIn(project_id=project["id"], name="mock_runtime_env", protocol="http", base_url="localhost", port=8000), admin, db)
    create_mock(
        MockEndpointIn(
            project_id=project["id"],
            environment_id=environment["id"],
            name="订单Mock",
            method="GET",
            path="/api/orders/1",
            status_code=202,
            headers={"X-Mock-Source": "platform"},
            response_body="<RESPONSE><STATUS>0</STATUS></RESPONSE>",
            body_format="xml",
        ),
        admin,
        db,
    )

    app = FastAPI()
    app.include_router(mock_router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.get(f"/mock-api/env/{environment['id']}/api/orders/1")
    missing = client.post(f"/mock-api/env/{environment['id']}/api/orders/1")

    assert response.status_code == 202
    assert response.headers["x-mock-source"] == "platform"
    assert response.headers["content-type"].startswith("application/xml")
    assert response.text == "<RESPONSE><STATUS>0</STATUS></RESPONSE>"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "未匹配到 Mock 规则"
 
 
def test_mock_api_appends_sm3_signature_when_enabled(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="mock_sm3_project", description="mock sm3"), admin, db)
    environment = create_environment(EnvironmentIn(project_id=project["id"], name="mock_sm3_env", protocol="http", base_url="localhost", port=8000), admin, db)
    response_body = "<RESPONSE><STATUS>0</STATUS></RESPONSE>"
    create_mock(
        MockEndpointIn(
            project_id=project["id"],
            environment_id=environment["id"],
            name="SM3响应Mock",
            method="POST",
            path="/api/sm3-response",
            status_code=200,
            response_body=response_body,
            body_format="xml",
            sm3_enabled=True,
        ),
        admin,
        db,
    )

    app = FastAPI()
    app.include_router(mock_router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    response = client.post(f"/mock-api/env/{environment['id']}/api/sm3-response")

    assert response.status_code == 200
    assert response.text == response_body + crypto_envelope.sm3_hex(response_body)


def test_create_user_defaults_active_and_can_login(db_session):
    db, admin = db_session
    created = create_user(UserCreate(username="tester_a", password="123456", real_name="测试A"), admin, db)

    assert created.username == "tester_a"
    assert created.real_name == "测试A"
    assert created.role == "tester"
    assert created.status == "active"

    result = login(LoginIn(username="tester_a", password="123456"), Response(), db)
    assert result["user"].username == "tester_a"


def test_list_users_paginates_and_searches(db_session):
    db, admin = db_session
    for index in range(12):
        create_user(UserCreate(username=f"page_user_{index}", password="123456", real_name=f"用户{index}"), admin, db)
    needle = create_user(UserCreate(username="needle_user", password="123456", real_name="命中"), admin, db)
    update_user_status(needle.id, UserStatusUpdate(status="disabled"), admin, db)

    first_page = list_users(page=1, page_size=50, _=admin, db=db)
    assert first_page["total"] == 14
    assert first_page["page_size"] == 10
    assert len(first_page["items"]) == 10

    second_page = list_users(page=2, page_size=10, _=admin, db=db)
    assert len(second_page["items"]) == 4

    searched = list_users(username="needle", page=1, page_size=10, _=admin, db=db)
    assert searched["total"] == 1
    assert searched["items"][0].username == "needle_user"

    active_users = list_users(status="active", page=1, page_size=10, _=admin, db=db)
    assert active_users["total"] == 13

    disabled_users = list_users(status="disabled", page=1, page_size=10, _=admin, db=db)
    assert disabled_users["total"] == 1
    assert disabled_users["items"][0].username == "needle_user"


def test_update_user_and_reject_duplicate_username(db_session):
    db, admin = db_session
    first = create_user(UserCreate(username="first_user", password="123456", real_name="一号"), admin, db)
    second = create_user(UserCreate(username="second_user", password="123456", real_name="二号"), admin, db)

    updated = update_user(second.id, UserUpdate(username="second_new", real_name="二号新"), admin, db)
    assert updated.username == "second_new"
    assert updated.real_name == "二号新"

    with pytest.raises(HTTPException) as error:
        update_user(second.id, UserUpdate(username=first.username, real_name="重复"), admin, db)
    assert error.value.status_code == 400


def test_disabled_user_cannot_login_until_enabled(db_session):
    db, admin = db_session
    created = create_user(UserCreate(username="toggle_user", password="123456", real_name="切换"), admin, db)

    disabled = update_user_status(created.id, UserStatusUpdate(status="disabled"), admin, db)
    assert disabled.status == "disabled"
    with pytest.raises(HTTPException):
        login(LoginIn(username="toggle_user", password="123456"), Response(), db)

    enabled = update_user_status(created.id, UserStatusUpdate(status="active"), admin, db)
    assert enabled.status == "active"
    result = login(LoginIn(username="toggle_user", password="123456"), Response(), db)
    assert result["user"].username == "toggle_user"


def test_tester_can_manage_users_except_create(db_session):
    db, admin = db_session
    tester = create_user(UserCreate(username="tester_manager", password="123456", real_name="普通用户"), admin, db)
    target = create_user(UserCreate(username="managed_user", password="123456", real_name="被管理用户"), admin, db)

    app = FastAPI()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.include_router(users_router)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {create_session_token(tester.id)}"}

    list_response = client.get("/users?page=1&page_size=10", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 3

    update_response = client.put(
        f"/users/{target.id}",
        headers=headers,
        json={"username": "managed_user_new", "real_name": "被管理用户新"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["username"] == "managed_user_new"

    status_response = client.patch(f"/users/{target.id}/status", headers=headers, json={"status": "disabled"})
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "disabled"

    create_response = client.post(
        "/users",
        headers=headers,
        json={"username": "forbidden_create", "password": "123456", "real_name": "禁止创建", "role": "tester"},
    )
    assert create_response.status_code == 403


def test_role_management_and_user_role_binding(db_session):
    db, admin = db_session
    ensure_default_roles(db)

    listed = list_roles(page=1, page_size=10, _=admin, db=db)
    assert {item["code"] for item in listed["items"]} >= {"admin", "tester"}

    role = create_role(
        RoleIn(code="reviewer", name="审核人员", description="只查看报告", menus=["dashboard", "reports"]),
        admin,
        db,
    )
    assert role["menus"] == ["dashboard", "reports"]

    updated = update_role(
        role["id"],
        RoleUpdate(name="审核专员", description="查看报告和日志", menus=["dashboard", "reports", "logs"]),
        admin,
        db,
    )
    assert updated["name"] == "审核专员"
    assert "logs" in updated["menus"]

    created_user = create_user(UserCreate(username="reviewer_user", password="123456", real_name="审核", role="reviewer"), admin, db)
    assert created_user.role == "reviewer"
    assert created_user.role_name == "审核专员"

    with pytest.raises(HTTPException) as bound_error:
        delete_role(role["id"], admin, db)
    assert bound_error.value.status_code == 400

    db.delete(db.query(User).filter(User.username == "reviewer_user").first())
    db.commit()
    deleted = delete_role(role["id"], admin, db)
    assert deleted["code"] == "reviewer"

    builtin = db.query(Role).filter(Role.code == "tester").first()
    with pytest.raises(HTTPException) as builtin_error:
        delete_role(builtin.id, admin, db)
    assert builtin_error.value.status_code == 400


def test_role_menu_permission_blocks_hidden_module(db_session):
    db, admin = db_session
    ensure_default_roles(db)
    role = create_role(RoleIn(code="report_only", name="报告查看", menus=["dashboard", "reports"]), admin, db)
    user = create_user(UserCreate(username="report_only_user", password="123456", real_name="报告", role=role["code"]), admin, db)

    app = FastAPI()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.include_router(users_router)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {create_session_token(user.id)}"}

    response = client.get("/users?page=1&page_size=10", headers=headers)
    assert response.status_code == 403


def test_change_password_validates_old_and_same_password(db_session):
    db, admin = db_session
    created = create_user(UserCreate(username="change_password_user", password="123456", real_name="改密用户"), admin, db)
    user = db.get(User, created.id)

    with pytest.raises(HTTPException) as wrong_old:
        change_password(ChangePasswordIn(old_password="bad-pass", new_password="654321"), user, db)
    assert wrong_old.value.status_code == 400

    with pytest.raises(HTTPException) as same_password:
        change_password(ChangePasswordIn(old_password="123456", new_password="123456"), user, db)
    assert same_password.value.status_code == 400


def test_change_password_allows_new_password_login_only(db_session):
    db, admin = db_session
    created = create_user(UserCreate(username="password_login_user", password="123456", real_name="登录改密用户"), admin, db)
    user = db.get(User, created.id)

    result = change_password(ChangePasswordIn(old_password="123456", new_password="newpass1"), user, db)
    assert result == {"ok": True}

    with pytest.raises(HTTPException):
        login(LoginIn(username="password_login_user", password="123456"), Response(), db)

    login_result = login(LoginIn(username="password_login_user", password="newpass1"), Response(), db)
    assert login_result["user"].username == "password_login_user"


def test_project_crud_keeps_full_list_and_supports_pagination_and_search(db_session):
    db, admin = db_session
    for index in range(12):
        create_project(ProjectIn(name=f"page_project_{index}", description=f"描述{index}"), admin, db)
    needle = create_project(ProjectIn(name="needle_project", description="命中", status="disabled"), admin, db)
    assert needle["status"] == "active"

    full_list = list_projects(_=admin, db=db)
    assert isinstance(full_list, list)
    assert len(full_list) == 13

    first_page = list_projects(page=1, page_size=10, _=admin, db=db)
    assert first_page["total"] == 13
    assert first_page["page_size"] == 10
    assert len(first_page["items"]) == 10

    second_page = list_projects(page=2, page_size=10, _=admin, db=db)
    assert len(second_page["items"]) == 3

    searched = list_projects(name="needle", page=1, page_size=10, _=admin, db=db)
    assert searched["total"] == 1
    assert searched["items"][0]["name"] == "needle_project"


def test_update_project(db_session):
    db, admin = db_session
    created = create_project(ProjectIn(name="old_project", description="旧描述"), admin, db)

    updated = update_project(created["id"], ProjectUpdate(name="new_project", description="新描述"), admin, db)
    assert updated["name"] == "new_project"
    assert updated["description"] == "新描述"


def test_create_project_requires_name_and_description(db_session):
    db, admin = db_session
    with pytest.raises(HTTPException) as name_error:
        create_project(ProjectIn(name="", description="描述"), admin, db)
    assert name_error.value.status_code == 400

    with pytest.raises(HTTPException) as description_error:
        create_project(ProjectIn(name="required_project", description=""), admin, db)
    assert description_error.value.status_code == 400


def test_create_project_rejects_duplicate_active_name_but_allows_deleted_name(db_session):
    db, admin = db_session
    first = create_project(ProjectIn(name="duplicate_project", description="第一个"), admin, db)

    with pytest.raises(HTTPException) as duplicate_error:
        create_project(ProjectIn(name="duplicate_project", description="重复"), admin, db)
    assert duplicate_error.value.status_code == 400

    delete_project(first["id"], admin, db)
    recreated = create_project(ProjectIn(name="duplicate_project", description="重建"), admin, db)
    assert recreated["name"] == "duplicate_project"
    assert recreated["is_deleted"] is False


def test_delete_project_is_logical_and_excluded_from_lists(db_session):
    db, admin = db_session
    keep = create_project(ProjectIn(name="keep_project", description="保留"), admin, db)
    deleted = create_project(ProjectIn(name="delete_project", description="删除"), admin, db)

    result = delete_project(deleted["id"], admin, db)
    assert result["is_deleted"] is True

    stored = db.get(Project, deleted["id"])
    assert stored is not None
    assert stored.is_deleted is True

    full_list = list_projects(_=admin, db=db)
    assert [row["id"] for row in full_list] == [keep["id"]]

    paged = list_projects(page=1, page_size=10, _=admin, db=db)
    assert paged["total"] == 1
    assert [row["id"] for row in paged["items"]] == [keep["id"]]

    searched = list_projects(name="delete", page=1, page_size=10, _=admin, db=db)
    assert searched["total"] == 0


def test_deleted_project_cannot_be_updated_or_deleted_again(db_session):
    db, admin = db_session
    created = create_project(ProjectIn(name="deleted_project", description="删除"), admin, db)
    delete_project(created["id"], admin, db)

    with pytest.raises(HTTPException) as update_error:
        update_project(created["id"], ProjectUpdate(name="new_name", description="新描述"), admin, db)
    assert update_error.value.status_code == 404

    with pytest.raises(HTTPException) as delete_error:
        delete_project(created["id"], admin, db)
    assert delete_error.value.status_code == 404

    with pytest.raises(HTTPException) as missing_error:
        delete_project(99999, admin, db)
    assert missing_error.value.status_code == 404


def test_environment_crud_paginates_and_searches(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="env_project", description="环境项目"), admin, db)
    other_project = create_project(ProjectIn(name="env_other_project", description="其它项目"), admin, db)
    for index in range(12):
        create_environment(EnvironmentIn(project_id=project["id"], name=f"env_{index}", protocol="https", base_url=f"env{index}.example.com"), admin, db)
    needle = create_environment(EnvironmentIn(project_id=project["id"], name="needle_env", protocol="https", base_url="needle.example.com"), admin, db)
    same_name_other_project = create_environment(EnvironmentIn(project_id=other_project["id"], name="needle_env", protocol="https", base_url="other.example.com"), admin, db)

    full_list = list_environments(_=admin, db=db)
    assert isinstance(full_list, list)
    assert len(full_list) == 14
    assert full_list[0]["project_name"] == "env_other_project"

    first_page = list_environments(page=1, page_size=50, _=admin, db=db)
    assert first_page["total"] == 14
    assert first_page["page_size"] == 10
    assert len(first_page["items"]) == 10

    project_filtered = list_environments(project_id=project["id"], page=1, page_size=10, _=admin, db=db)
    assert project_filtered["total"] == 13

    searched = list_environments(project_id=project["id"], name="needle", page=1, page_size=10, _=admin, db=db)
    assert searched["total"] == 1
    assert searched["items"][0]["id"] == needle["id"]
    assert searched["items"][0]["protocol"] == "https"
    assert searched["items"][0]["port"] == 443

    other_searched = list_environments(project_id=other_project["id"], name="needle", page=1, page_size=10, _=admin, db=db)
    assert other_searched["total"] == 1
    assert other_searched["items"][0]["id"] == same_name_other_project["id"]


def test_create_environment_validates_required_project_and_duplicate_name(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="env_required_project", description="环境项目"), admin, db)
    other_project = create_project(ProjectIn(name="env_required_other", description="其它项目"), admin, db)
    create_environment(EnvironmentIn(project_id=project["id"], name="test", protocol="https", base_url="test.example.com"), admin, db)

    with pytest.raises(HTTPException) as project_error:
        create_environment(EnvironmentIn(project_id=99999, name="missing", protocol="https", base_url="missing.example.com"), admin, db)
    assert project_error.value.status_code == 404

    with pytest.raises(HTTPException) as name_error:
        create_environment(EnvironmentIn(project_id=project["id"], name="", protocol="https", base_url="empty.example.com"), admin, db)
    assert name_error.value.status_code == 400

    with pytest.raises(HTTPException) as url_error:
        create_environment(EnvironmentIn(project_id=project["id"], name="empty_url", protocol="https", base_url=""), admin, db)
    assert url_error.value.status_code == 400

    with pytest.raises(HTTPException) as duplicate_error:
        create_environment(EnvironmentIn(project_id=project["id"], name="test", protocol="https", base_url="dup.example.com"), admin, db)
    assert duplicate_error.value.status_code == 400

    same_name_other_project = create_environment(EnvironmentIn(project_id=other_project["id"], name="test", protocol="https", base_url="other.example.com"), admin, db)
    assert same_name_other_project["name"] == "test"


def test_create_environment_protocol_and_port_defaults(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="env_protocol_project", description="环境项目"), admin, db)

    http_env = create_environment(EnvironmentIn(project_id=project["id"], name="http_env", protocol="http", base_url="http.example.com"), admin, db)
    assert http_env["protocol"] == "http"
    assert http_env["port"] == 80

    https_env = create_environment(EnvironmentIn(project_id=project["id"], name="https_env", protocol="https", base_url="https.example.com"), admin, db)
    assert https_env["protocol"] == "https"
    assert https_env["port"] == 443

    custom_port = create_environment(EnvironmentIn(project_id=project["id"], name="custom_port_env", protocol="https", base_url="custom.example.com", port=8443), admin, db)
    assert custom_port["port"] == 8443

    with pytest.raises(HTTPException) as port_error:
        create_environment(EnvironmentIn(project_id=project["id"], name="bad_port_env", protocol="https", base_url="bad.example.com", port=0), admin, db)
    assert port_error.value.status_code == 400


def test_update_environment_and_reject_duplicate_name(db_session):
    db, admin = db_session
    first_project = create_project(ProjectIn(name="env_update_project", description="环境项目"), admin, db)
    second_project = create_project(ProjectIn(name="env_update_other", description="其它项目"), admin, db)
    first = create_environment(EnvironmentIn(project_id=first_project["id"], name="first", protocol="https", base_url="first.example.com"), admin, db)
    create_environment(EnvironmentIn(project_id=second_project["id"], name="duplicate", protocol="https", base_url="dup.example.com"), admin, db)

    updated = update_environment(first["id"], EnvironmentUpdate(project_id=second_project["id"], name="first_new", protocol="http", base_url="new.example.com", port=8080), admin, db)
    assert updated["project_id"] == second_project["id"]
    assert updated["project_name"] == "env_update_other"
    assert updated["name"] == "first_new"
    assert updated["protocol"] == "http"
    assert updated["base_url"] == "new.example.com"
    assert updated["port"] == 8080

    with pytest.raises(HTTPException) as duplicate_error:
        update_environment(first["id"], EnvironmentUpdate(project_id=second_project["id"], name="duplicate", protocol="https", base_url="dup2.example.com"), admin, db)
    assert duplicate_error.value.status_code == 400


def test_delete_environment_is_logical_and_excluded_from_lists(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="env_delete_project", description="环境项目"), admin, db)
    keep = create_environment(EnvironmentIn(project_id=project["id"], name="keep_env", protocol="https", base_url="keep.example.com"), admin, db)
    deleted = create_environment(EnvironmentIn(project_id=project["id"], name="delete_env", protocol="https", base_url="delete.example.com"), admin, db)

    result = delete_environment(deleted["id"], admin, db)
    assert result["is_deleted"] is True

    stored = db.get(Environment, deleted["id"])
    assert stored is not None
    assert stored.is_deleted is True

    full_list = list_environments(_=admin, db=db)
    assert [row["id"] for row in full_list] == [keep["id"]]

    paged = list_environments(page=1, page_size=10, _=admin, db=db)
    assert paged["total"] == 1
    assert [row["id"] for row in paged["items"]] == [keep["id"]]

    searched = list_environments(name="delete", page=1, page_size=10, _=admin, db=db)
    assert searched["total"] == 0

    recreated = create_environment(EnvironmentIn(project_id=project["id"], name="delete_env", protocol="https", base_url="recreated.example.com"), admin, db)
    assert recreated["is_deleted"] is False


def test_deleted_environment_cannot_be_updated_or_deleted_again(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="env_deleted_project", description="环境项目"), admin, db)
    created = create_environment(EnvironmentIn(project_id=project["id"], name="deleted_env", protocol="https", base_url="deleted.example.com"), admin, db)
    delete_environment(created["id"], admin, db)

    with pytest.raises(HTTPException) as update_error:
        update_environment(created["id"], EnvironmentUpdate(project_id=project["id"], name="new_env", protocol="https", base_url="new.example.com"), admin, db)
    assert update_error.value.status_code == 404

    with pytest.raises(HTTPException) as delete_error:
        delete_environment(created["id"], admin, db)
    assert delete_error.value.status_code == 404


def test_api_crud_paginates_and_searches(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="api_project", description="api project"), admin, db)
    other_project = create_project(ProjectIn(name="api_other_project", description="other project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    other_environment = create_test_environment(other_project["id"], admin, db)
    for index in range(12):
        create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name=f"api_{index}", method="GET", path=f"/api/{index}"), admin, db)
    needle = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="needle_api", method="POST", path="/needle/url", description="target api"), admin, db)
    same_name_other_project = create_api(ApiDefinitionIn(project_id=other_project["id"], environment_id=other_environment["id"], name="needle_api", method="GET", path="/other/needle"), admin, db)

    full_list = list_apis(_=admin, db=db)
    assert isinstance(full_list, list)
    assert len(full_list) == 14
    assert full_list[0]["project_name"] == "api_other_project"
    assert full_list[0]["environment_name"] == "env_{}".format(other_project["id"])

    first_page = list_apis(page=1, page_size=50, _=admin, db=db)
    assert first_page["total"] == 14
    assert first_page["page_size"] == 10
    assert len(first_page["items"]) == 10

    project_filtered = list_apis(project_id=project["id"], page=1, page_size=10, _=admin, db=db)
    assert project_filtered["total"] == 13

    environment_filtered = list_apis(environment_id=environment["id"], page=1, page_size=10, _=admin, db=db)
    assert environment_filtered["total"] == 13

    name_searched = list_apis(project_id=project["id"], name="needle", page=1, page_size=10, _=admin, db=db)
    assert name_searched["total"] == 1
    assert name_searched["items"][0]["id"] == needle["id"]
    assert name_searched["items"][0]["description"] == "target api"

    url_searched = list_apis(project_id=project["id"], url="/needle", page=1, page_size=10, _=admin, db=db)
    assert url_searched["total"] == 1
    assert url_searched["items"][0]["id"] == needle["id"]

    other_searched = list_apis(project_id=other_project["id"], name="needle", page=1, page_size=10, _=admin, db=db)
    assert other_searched["total"] == 1
    assert other_searched["items"][0]["id"] == same_name_other_project["id"]


def test_create_api_validates_required_project_name_path_and_duplicate_name(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="api_required_project", description="api project"), admin, db)
    other_project = create_project(ProjectIn(name="api_required_other", description="other project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    other_environment = create_test_environment(other_project["id"], admin, db)
    created = create_api(ApiDefinitionIn(project_id=project["id"], name="login", method="POST", path="/login", module="legacy", headers={"A": "B"}, query={"q": 1}, body={"format": "json", "template": {"username": "${username}"}}, description="login api", pre_script="pm.environment.set('requestId', Date.now());"), admin, db)

    assert created["environment_id"] == 0
    assert created["environment_name"] == ""
    assert created["module"] == ""
    assert created["headers"] == {"A": "B"}
    assert created["query"] == {"q": 1}
    assert created["body"] == {"format": "json", "template": {"username": "${username}"}}
    assert created["description"] == "login api"
    assert created["pre_script"] == "pm.environment.set('requestId', Date.now());"
    assert created["auth"]["type"] == "none"

    with pytest.raises(HTTPException) as project_error:
        create_api(ApiDefinitionIn(project_id=99999, environment_id=environment["id"], name="missing", method="GET", path="/missing"), admin, db)
    assert project_error.value.status_code == 404

    historical_environment = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=other_environment["id"], name="historical_env", method="GET", path="/historical-env"), admin, db)
    assert historical_environment["environment_id"] == other_environment["id"]

    with pytest.raises(HTTPException) as name_error:
        create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="", method="GET", path="/empty"), admin, db)
    assert name_error.value.status_code == 400

    with pytest.raises(HTTPException) as path_error:
        create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="empty_path", method="GET", path=""), admin, db)
    assert path_error.value.status_code == 400

    with pytest.raises(HTTPException) as duplicate_error:
        create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="login", method="GET", path="/duplicate"), admin, db)
    assert duplicate_error.value.status_code == 400

    same_name_other_project = create_api(ApiDefinitionIn(project_id=other_project["id"], environment_id=other_environment["id"], name="login", method="GET", path="/login"), admin, db)
    assert same_name_other_project["name"] == "login"


def test_update_api_and_reject_duplicate_name(db_session):
    db, admin = db_session
    first_project = create_project(ProjectIn(name="api_update_project", description="api project"), admin, db)
    second_project = create_project(ProjectIn(name="api_update_other", description="other project"), admin, db)
    first_environment = create_test_environment(first_project["id"], admin, db)
    second_environment = create_test_environment(second_project["id"], admin, db)
    first = create_api(ApiDefinitionIn(project_id=first_project["id"], environment_id=first_environment["id"], name="first_api", method="GET", path="/first"), admin, db)
    create_api(ApiDefinitionIn(project_id=second_project["id"], environment_id=second_environment["id"], name="duplicate_api", method="GET", path="/duplicate"), admin, db)

    updated = update_api(
        first["id"],
        ApiDefinitionUpdate(
            project_id=second_project["id"],
            name="first_new",
            method="PUT",
            path="/new",
            headers={"Content-Type": "application/json", "Authorization": "Bearer abc"},
            query={"page": "1"},
            body={"format": "xml", "template": "<request><token>${token}</token></request>"},
            description="new description",
            pre_script="pm.environment.set('signature', CryptoJS.MD5('payload').toString());",
            auth={
                "type": "bearer",
                "add_to": "headers",
                "header_name": "Authorization",
                "header_prefix": "Bearer",
                "token": "${api_token}",
            },
        ),
        admin,
        db,
    )
    assert updated["project_id"] == second_project["id"]
    assert updated["environment_id"] == 0
    assert updated["project_name"] == "api_update_other"
    assert updated["environment_name"] == ""
    assert updated["name"] == "first_new"
    assert updated["method"] == "PUT"
    assert updated["path"] == "/new"
    assert updated["headers"] == {"Content-Type": "application/json", "Authorization": "Bearer abc"}
    assert updated["query"] == {"page": "1"}
    assert updated["body"] == {"format": "xml", "template": "<request><token>${token}</token></request>"}
    assert updated["description"] == "new description"
    assert updated["pre_script"] == "pm.environment.set('signature', CryptoJS.MD5('payload').toString());"
    assert updated["auth"]["type"] == "bearer"
    assert updated["auth"]["token"] == "${api_token}"

    with pytest.raises(HTTPException) as duplicate_error:
        update_api(first["id"], ApiDefinitionUpdate(project_id=second_project["id"], environment_id=second_environment["id"], name="duplicate_api", method="GET", path="/dup2"), admin, db)
    assert duplicate_error.value.status_code == 400

    historical_update = update_api(first["id"], ApiDefinitionUpdate(project_id=first_project["id"], environment_id=second_environment["id"], name="historical_env_update", method="GET", path="/historical-env"), admin, db)
    assert historical_update["environment_id"] == second_environment["id"]


def test_auth_config_injects_headers_and_query(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="api_auth_project", description="api auth"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    env = db.get(Environment, environment["id"])

    headers = {}
    query = {}
    _apply_auth_config(
        {"type": "bearer", "header_name": "Authorization", "header_prefix": "Bearer", "token": "${token}"},
        env,
        "/users",
        headers,
        query,
        {"token": "abc"},
        {},
    )
    assert headers["Authorization"] == "Bearer abc"

    headers = {"Authorization": "Bearer case-token"}
    _apply_auth_config(
        {"type": "bearer", "header_name": "Authorization", "header_prefix": "Bearer", "token": "api-token"},
        env,
        "/users",
        headers,
        {},
        {},
        {},
    )
    assert headers["Authorization"] == "Bearer case-token"

    query = {}
    _apply_auth_config(
        {"type": "api_key", "add_to": "query", "api_key_name": "appId", "api_key_value": "${app_id}"},
        env,
        "/users",
        {},
        query,
        {"app_id": "1001"},
        {},
    )
    assert query["appId"] == "1001"


def test_oauth2_auth_config_can_add_token_to_query(db_session, monkeypatch):
    db, admin = db_session
    project = create_project(ProjectIn(name="oauth_query_project", description="api auth"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    env = db.get(Environment, environment["id"])
    monkeypatch.setattr(executor_service, "_request_oauth2_client_credentials_token", lambda *args, **kwargs: "oauth-token")

    headers = {}
    query = {}
    _apply_auth_config(
        {
            "type": "oauth2_client_credentials",
            "add_to": "query",
            "token_url": "http://example.test/OAuth/Oauth/Token",
            "client_id": "client",
            "client_secret": "secret",
        },
        env,
        "/users",
        headers,
        query,
        {},
        {},
    )
    assert query["access_token"] == "oauth-token"
    assert "Authorization" not in headers


def test_oauth2_token_request_uses_configurable_grant_type_and_tls_verify(db_session, monkeypatch):
    db, admin = db_session
    project = create_project(ProjectIn(name="oauth_request_project", description="api auth"), admin, db)
    environment = create_environment(EnvironmentIn(project_id=project["id"], name="oauth_env", protocol="https", base_url="example.test", variables={"grant_type": "client_credentials"}), admin, db)
    env = db.get(Environment, environment["id"])
    captured = {}

    class FakeResponse:
        status_code = 200
        text = '{"access_token":"preview-token"}'

    class FakeClient:
        def __init__(self, timeout, verify):
            captured["timeout"] = timeout
            captured["verify"] = verify

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, data, headers, auth):
            captured["url"] = url
            captured["data"] = data
            captured["headers"] = headers
            captured["auth"] = auth
            return FakeResponse()

    monkeypatch.setattr(executor_service.httpx, "Client", FakeClient)
    token = _request_oauth2_client_credentials_token(
        {
            "token_url": "https://example.test/OAuth",
            "grant_type": "${grant_type}",
            "client_id": "masterAPI",
            "client_secret": "1234",
            "scope": "https://example.test/PAPI/api/Cms/GetContractList",
            "client_authentication": "body",
            "verify_tls": False,
        },
        env,
        "https://example.test/PAPI/api/Cms/GetContractList",
        {"grant_type": "client_credentials"},
    )

    assert token == "preview-token"
    assert captured["verify"] is False
    assert captured["data"] == {
        "grant_type": "client_credentials",
        "scope": "https://example.test/PAPI/api/Cms/GetContractList",
        "client_id": "masterAPI",
        "client_secret": "1234",
    }
    assert captured["headers"] == {"Content-Type": "application/x-www-form-urlencoded"}


def test_delete_api_removes_unreferenced_and_rejects_referenced(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="api_delete_project", description="api project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    unreferenced = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="unreferenced_api", method="GET", path="/free"), admin, db)
    referenced = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="referenced_api", method="GET", path="/used"), admin, db)
    db.add(TestCaseModel(project_id=project["id"], api_id=referenced["id"], name="uses_api"))
    db.commit()

    deleted = delete_api(unreferenced["id"], admin, db)
    assert deleted["id"] == unreferenced["id"]
    assert list_apis(name="unreferenced", page=1, page_size=10, _=admin, db=db)["total"] == 0

    with pytest.raises(HTTPException) as referenced_error:
        delete_api(referenced["id"], admin, db)
    assert referenced_error.value.status_code == 400

    referenced_case = db.query(TestCaseModel).filter(TestCaseModel.api_id == referenced["id"]).first()
    deleted_case = delete_case(referenced_case.id, admin, db)
    assert deleted_case["is_deleted"] is True
    deleted_referenced_api = delete_api(referenced["id"], admin, db)
    assert deleted_referenced_api["id"] == referenced["id"]

    with pytest.raises(HTTPException) as missing_error:
        delete_api(99999, admin, db)
    assert missing_error.value.status_code == 404


def test_delete_case_rejects_when_referenced_by_test_plan(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="case_delete_project", description="case delete project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    api_row = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="case_delete_api", method="GET", path="/case"), admin, db)
    referenced_case = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="referenced_case"), admin, db)
    free_case = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="free_case"), admin, db)
    plan = create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=api_row["id"], name="引用用例的计划", items=[referenced_case["id"]]), admin, db)

    with pytest.raises(HTTPException) as referenced_error:
        delete_case(referenced_case["id"], admin, db)
    assert referenced_error.value.status_code == 400
    assert "该用例已被测试计划引用" in referenced_error.value.detail
    assert "引用用例的计划" in referenced_error.value.detail

    deleted_free_case = delete_case(free_case["id"], admin, db)
    assert deleted_free_case["is_deleted"] is True

    delete_plan(plan["id"], admin, db)
    deleted_referenced_case = delete_case(referenced_case["id"], admin, db)
    assert deleted_referenced_case["is_deleted"] is True


def test_create_and_filter_cases_by_project_and_api(db_session):
    db, admin = db_session
    first_project = create_project(ProjectIn(name="case_project_first", description="case project"), admin, db)
    second_project = create_project(ProjectIn(name="case_project_second", description="case project"), admin, db)
    first_api = create_api(ApiDefinitionIn(project_id=first_project["id"], name="case_api_first", method="POST", path="/first"), admin, db)
    second_api = create_api(ApiDefinitionIn(project_id=second_project["id"], name="case_api_second", method="GET", path="/second"), admin, db)

    created = create_case(
        TestCaseIn(
            project_id=first_project["id"],
            api_id=first_api["id"],
            name="first_case",
            request_body={"username": "tester"},
            extractors=[{"name": "token", "path": "$.data.token"}],
        ),
        admin,
        db,
    )
    create_case(
        TestCaseIn(
            project_id=second_project["id"],
            api_id=second_api["id"],
            name="second_case",
            request_body={"page": 1},
            assertions=[{"type": "body_contains", "expected": "ok"}],
        ),
        admin,
        db,
    )

    assert created["project_name"] == "case_project_first"
    assert created["api_name"] == "case_api_first"
    assert created["request_body"] == {"username": "tester"}
    assert created["extractors"] == [{"name": "token", "path": "$.data.token", "source": "jsonpath"}]
    assert "priority" not in created
    assert "status" not in created
    assert created["is_deleted"] is False
    assert created["assertions"] == []

    paged = list_cases(page=1, page_size=10, _=admin, db=db)
    assert paged["total"] == 2
    assert paged["page"] == 1
    assert paged["page_size"] == 10
    assert [item["name"] for item in paged["items"]] == ["first_case", "second_case"]

    first_project_cases = list_cases(project_id=first_project["id"], _=admin, db=db)
    assert [item["name"] for item in first_project_cases] == ["first_case"]

    first_api_cases = list_cases(api_id=first_api["id"], _=admin, db=db)
    assert [item["name"] for item in first_api_cases] == ["first_case"]

    second_project_paged = list_cases(project_id=second_project["id"], api_id=second_api["id"], page=1, page_size=10, _=admin, db=db)
    assert second_project_paged["total"] == 1
    assert second_project_paged["items"][0]["assertions"] == [{"type": "body_contains", "path": "", "expected": "ok"}]

    with pytest.raises(HTTPException) as mismatch_error:
        create_case(
            TestCaseIn(project_id=first_project["id"], api_id=second_api["id"], name="mismatch_case"),
            admin,
            db,
        )
    assert mismatch_error.value.status_code == 400


def test_update_and_logically_delete_case(db_session):
    db, admin = db_session
    first_project = create_project(ProjectIn(name="case_update_first", description="case project"), admin, db)
    second_project = create_project(ProjectIn(name="case_update_second", description="case project"), admin, db)
    first_api = create_api(ApiDefinitionIn(project_id=first_project["id"], name="case_update_api_first", method="POST", path="/first"), admin, db)
    second_api = create_api(ApiDefinitionIn(project_id=second_project["id"], name="case_update_api_second", method="GET", path="/second"), admin, db)
    created = create_case(TestCaseIn(project_id=first_project["id"], api_id=first_api["id"], name="old_case"), admin, db)

    updated = update_case(
        created["id"],
        TestCaseUpdate(
            project_id=second_project["id"],
            api_id=second_api["id"],
            name="updated_case",
            request_body={"updated": True},
            assertions=[{"type": "jsonpath_equal", "path": "$.code", "expected": 0}],
            extractors=[{"name": "userId", "path": "$.data.userId"}],
            tags="updated description",
        ),
        admin,
        db,
    )
    assert updated["project_id"] == second_project["id"]
    assert updated["api_id"] == second_api["id"]
    assert updated["project_name"] == "case_update_second"
    assert updated["api_name"] == "case_update_api_second"
    assert updated["name"] == "updated_case"
    assert updated["request_body"] == {"updated": True}
    assert updated["assertions"] == [{"type": "jsonpath_equal", "path": "$.code", "expected": 0}]
    assert updated["extractors"] == [{"name": "userId", "path": "$.data.userId", "source": "jsonpath"}]
    assert updated["tags"] == "updated description"
    assert "priority" not in updated
    assert "status" not in updated

    with pytest.raises(HTTPException) as mismatch_error:
        update_case(
            created["id"],
            TestCaseUpdate(project_id=first_project["id"], api_id=second_api["id"], name="bad_case"),
            admin,
            db,
        )
    assert mismatch_error.value.status_code == 400

    deleted = delete_case(created["id"], admin, db)
    assert deleted["is_deleted"] is True
    assert list_cases(project_id=second_project["id"], _=admin, db=db) == []

    with pytest.raises(HTTPException) as update_deleted_error:
        update_case(
            created["id"],
            TestCaseUpdate(project_id=second_project["id"], api_id=second_api["id"], name="deleted_case"),
            admin,
            db,
        )
    assert update_deleted_error.value.status_code == 404

    with pytest.raises(HTTPException) as delete_again_error:
        delete_case(created["id"], admin, db)
    assert delete_again_error.value.status_code == 404


def test_plan_crud_paginates_searches_and_validates_relations(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="plan_project", description="plan project"), admin, db)
    other_project = create_project(ProjectIn(name="plan_other_project", description="other plan project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    second_environment = create_environment(EnvironmentIn(project_id=project["id"], name="plan_second_env", protocol="https", base_url="plan-second.example.com"), admin, db)
    other_environment = create_test_environment(other_project["id"], admin, db)
    api_row = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="plan_api", method="POST", path="/plan"), admin, db)
    same_project_other_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="plan_token_api", method="POST", path="/token"), admin, db)
    other_api = create_api(ApiDefinitionIn(project_id=other_project["id"], environment_id=other_environment["id"], name="other_plan_api", method="GET", path="/other"), admin, db)
    first_case = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="first_plan_case"), admin, db)
    second_case = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="second_plan_case"), admin, db)
    token_case = create_case(TestCaseIn(project_id=project["id"], api_id=same_project_other_api["id"], name="token_plan_case"), admin, db)
    other_case = create_case(TestCaseIn(project_id=other_project["id"], api_id=other_api["id"], name="other_plan_case"), admin, db)

    created = create_plan(
        TestPlanIn(
            project_id=project["id"],
            environment_id=environment["id"],
            api_id=api_row["id"],
            name="daily plan",
            items=[first_case["id"], second_case["id"]],
        ),
        admin,
        db,
    )
    assert created["name"] == "daily plan"
    assert created["project_name"] == "plan_project"
    assert created["environment_name"] == f"env_{project['id']}"
    assert created["api_name"] == "plan_api"
    assert created["items"] == [
        {"case_id": first_case["id"], "environment_id": environment["id"]},
        {"case_id": second_case["id"], "environment_id": environment["id"]},
    ]
    assert [item["name"] for item in created["cases"]] == ["first_plan_case", "second_plan_case"]
    assert [item["environment_id"] for item in created["cases"]] == [environment["id"], environment["id"]]
    assert [item["status"] for item in created["cases"]] == ["", ""]
    assert created["creator_name"] == "Admin"

    execution_task = ExecutionTask(
        executor_id=admin.id,
        project_id=project["id"],
        environment_id=environment["id"],
        target_type="plan",
        target_id=created["id"],
        status="failed",
    )
    db.add(execution_task)
    db.commit()
    db.refresh(execution_task)
    db.add_all([
        ExecutionResult(task_id=execution_task.id, case_id=first_case["id"], status="passed"),
        ExecutionResult(task_id=execution_task.id, case_id=second_case["id"], status="failed"),
    ])
    stored_created_plan = db.get(TestSuite, created["id"])
    stored_created_plan.last_execution_id = execution_task.id
    stored_created_plan.last_status = "failed"
    db.commit()
    reloaded_created = list_plans(project_id=project["id"], name="daily", page=1, page_size=10, _=admin, db=db)["items"][0]
    assert [item["status"] for item in reloaded_created["cases"]] == ["passed", "failed"]

    with pytest.raises(HTTPException) as duplicate_error:
        create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=api_row["id"], name="daily plan", items=[first_case["id"]]), admin, db)
    assert duplicate_error.value.status_code == 400

    same_name_other_project = create_plan(TestPlanIn(project_id=other_project["id"], environment_id=other_environment["id"], api_id=other_api["id"], name="daily plan", items=[other_case["id"]]), admin, db)
    assert same_name_other_project["project_id"] == other_project["id"]

    with pytest.raises(HTTPException) as env_mismatch:
        create_plan(TestPlanIn(project_id=project["id"], environment_id=other_environment["id"], api_id=api_row["id"], name="bad env", items=[first_case["id"]]), admin, db)
    assert env_mismatch.value.status_code == 400

    with pytest.raises(HTTPException) as case_mismatch:
        create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=api_row["id"], name="bad case", items=[other_case["id"]]), admin, db)
    assert case_mismatch.value.status_code == 400

    mixed_api_plan = create_plan(
        TestPlanIn(
            project_id=project["id"],
            environment_id=environment["id"],
            api_id=api_row["id"],
            name="mixed api plan",
            items=[first_case["id"], {"case_id": token_case["id"], "environment_id": second_environment["id"]}],
        ),
        admin,
        db,
    )
    assert mixed_api_plan["items"] == [
        {"case_id": first_case["id"], "environment_id": environment["id"]},
        {"case_id": token_case["id"], "environment_id": second_environment["id"]},
    ]
    assert [item["environment_id"] for item in mixed_api_plan["cases"]] == [environment["id"], second_environment["id"]]
    assert mixed_api_plan["api_name"] == "plan_api、plan_token_api"

    paged = list_plans(project_id=project["id"], page=1, page_size=10, _=admin, db=db)
    assert paged["total"] == 2

    searched = list_plans(project_id=project["id"], api_id=api_row["id"], name="daily", page=1, page_size=10, _=admin, db=db)
    assert searched["total"] == 1

    token_api_searched = list_plans(project_id=project["id"], api_id=same_project_other_api["id"], name="mixed", page=1, page_size=10, _=admin, db=db)
    assert token_api_searched["total"] == 1
    assert token_api_searched["items"][0]["id"] == mixed_api_plan["id"]

    updated = update_plan(
        created["id"],
        TestPlanUpdate(project_id=project["id"], environment_id=environment["id"], api_id=api_row["id"], name="daily plan updated", items=[second_case["id"], first_case["id"]]),
        admin,
        db,
    )
    assert updated["items"] == [
        {"case_id": second_case["id"], "environment_id": environment["id"]},
        {"case_id": first_case["id"], "environment_id": environment["id"]},
    ]
    assert updated["last_status"] == "edited"
    assert updated["last_execution_id"] is None

    deleted = delete_plan(created["id"], admin, db)
    assert deleted["is_deleted"] is True
    assert list_plans(project_id=project["id"], page=1, page_size=10, _=admin, db=db)["total"] == 1


def test_execute_plan_creates_task_and_executor_syncs_status(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="plan_execute_project", description="plan execute project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    api_row = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="plan_execute_api", method="GET", path="/missing"), admin, db)
    case_row = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="execute_case"), admin, db)
    plan = create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=api_row["id"], name="execute plan", items=[case_row["id"]]), admin, db)

    task = execute_plan(plan["id"], admin, db)
    stored_task = db.get(ExecutionTask, task["id"])
    stored_plan = db.get(TestSuite, plan["id"])

    assert task["status"] == "queued"
    assert stored_task.target_type == "plan"
    assert stored_task.target_id == plan["id"]
    assert stored_plan.last_execution_id == task["id"]
    assert stored_plan.last_status == "queued"


def test_execute_plan_passes_extracted_variables_to_later_case_body(db_session, monkeypatch):
    db, admin = db_session
    project = create_project(ProjectIn(name="dependency_project", description="dependency project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    login_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="login_api", method="POST", path="/login"), admin, db)
    submit_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="submit_api", method="POST", path="/submit"), admin, db)
    login_case = create_case(
        TestCaseIn(
            project_id=project["id"],
            api_id=login_api["id"],
            name="login_case",
            extractors=[
                {"name": "token", "path": "$.data.token"},
                {"name": "missingValue", "path": "$.data.missing"},
            ],
        ),
        admin,
        db,
    )
    submit_case = create_case(
        TestCaseIn(
            project_id=project["id"],
            api_id=submit_api["id"],
            name="submit_case",
            request_body={"authorization": "Bearer ${token}"},
        ),
        admin,
        db,
    )
    plan = create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=login_api["id"], name="dependency plan", items=[login_case["id"], submit_case["id"]]), admin, db)
    task = ExecutionTask(executor_id=admin.id, project_id=project["id"], environment_id=environment["id"], target_type="plan", target_id=plan["id"], status="running")
    db.add(task)
    db.commit()
    db.refresh(task)
    requests = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, headers=None, params=None, json=None):
            requests.append({"method": method, "url": url, "json": json})
            if url.endswith("/login"):
                return executor_service.httpx.Response(200, json={"code": 0, "data": {"token": "abc123"}})
            return executor_service.httpx.Response(200, json={"code": 0, "ok": True})

    monkeypatch.setattr(executor_service.httpx, "Client", FakeClient)

    rows = _execute(db, task)
    first_response = executor_service.parse_json(rows[0].response_snapshot_json, {})
    second_request = executor_service.parse_json(rows[1].request_snapshot_json, {})

    assert len(rows) == 2
    assert requests[1]["json"] == {"authorization": "Bearer abc123"}
    assert second_request["body"] == {"authorization": "Bearer abc123"}
    assert first_response["extracted_variables"] == [
        {"name": "token", "path": "$.data.token", "source": "jsonpath", "value": "abc123", "success": True},
        {"name": "missingValue", "path": "$.data.missing", "source": "jsonpath", "value": None, "success": False},
    ]


def test_execute_stores_truncated_long_response_but_asserts_full_text(db_session, monkeypatch):
    db, admin = db_session
    project = create_project(ProjectIn(name="long_response_project", description="long response project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    api_row = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="long_response_api", method="GET", path="/long"), admin, db)
    case_row = create_case(
        TestCaseIn(
            project_id=project["id"],
            api_id=api_row["id"],
            name="long_response_case",
            assertions=[{"type": "body_contains", "expected": "TAIL_OK"}],
        ),
        admin,
        db,
    )
    task = ExecutionTask(executor_id=admin.id, project_id=project["id"], environment_id=environment["id"], target_type="case", target_id=case_row["id"], status="running")
    db.add(task)
    db.commit()
    db.refresh(task)

    class SmallSnapshotSettings:
        response_body_limit = 20

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, **kwargs):
            return executor_service.httpx.Response(200, text=("A" * 100) + "TAIL_OK")

    monkeypatch.setattr(executor_service, "get_settings", lambda: SmallSnapshotSettings())
    monkeypatch.setattr(executor_service.httpx, "Client", FakeClient)

    rows = _execute(db, task)
    response_snapshot = executor_service.parse_json(rows[0].response_snapshot_json, {})
    assertion_results = executor_service.parse_json(rows[0].assertion_results_json, [])

    assert rows[0].status == "passed"
    assert assertion_results[0]["passed"] is True
    assert response_snapshot["text"] == "A" * 20
    assert response_snapshot["text_truncated"] is True
    assert response_snapshot["text_original_length"] == 107
    assert response_snapshot["text_stored_length"] == 20


def test_execute_plan_appends_sm3_signature_to_rendered_xml_body(db_session, monkeypatch):
    db, admin = db_session
    project = create_project(ProjectIn(name="sm3_project", description="sm3 project"), admin, db)
    environment = create_environment(EnvironmentIn(project_id=project["id"], name="sm3_env", protocol="http", base_url="example.test", variables={"address": "测试地址"}), admin, db)
    api_row = create_api(
        ApiDefinitionIn(
            project_id=project["id"],
            environment_id=environment["id"],
            name="sm3_api",
            method="POST",
            path="/submit",
            body={"format": "xml", "template": "<REQUEST><ADDRESS>${address}</ADDRESS></REQUEST>"},
            encryption=EncryptionConfigIn(sm3_signature=True),
        ),
        admin,
        db,
    )
    body = "<REQUEST><ADDRESS>${address}</ADDRESS></REQUEST>"
    case_row = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="sm3_case", request_body=body), admin, db)
    plan = create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=api_row["id"], name="sm3 plan", items=[case_row["id"]]), admin, db)
    task = ExecutionTask(executor_id=admin.id, project_id=project["id"], environment_id=environment["id"], target_type="plan", target_id=plan["id"], status="running")
    db.add(task)
    db.commit()
    db.refresh(task)
    requests = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, headers=None, params=None, content=None, **kwargs):
            requests.append({"method": method, "url": url, "content": content})
            return executor_service.httpx.Response(200, json={"code": 0})

    monkeypatch.setattr(executor_service.httpx, "Client", FakeClient)

    rows = _execute(db, task)
    request_snapshot = executor_service.parse_json(rows[0].request_snapshot_json, {})
    rendered_body = "<REQUEST><ADDRESS>测试地址</ADDRESS></REQUEST>"
    signature = crypto_envelope.sm3_hex(rendered_body)

    assert rows[0].status == "passed"
    assert requests[0]["content"] == rendered_body + signature
    assert request_snapshot["body_original"] == rendered_body
    assert request_snapshot["body"] == rendered_body + signature
    assert request_snapshot["sm3_signature"]["value"] == signature
    assert request_snapshot["sm3_signature"]["source_length"] == len(rendered_body)


def test_execute_plan_rejects_sm3_signature_with_request_encryption(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="sm3_encrypt_project", description="sm3 encrypt project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    api_row = create_api(
        ApiDefinitionIn(
            project_id=project["id"],
            environment_id=environment["id"],
            name="sm3_encrypt_api",
            method="POST",
            path="/submit",
            body={"format": "xml", "template": "<REQUEST/>"},
            encryption=EncryptionConfigIn(mode="rsa_aes_sm3", encrypt_request=True, sm3_signature=True),
        ),
        admin,
        db,
    )
    case_row = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="sm3_encrypt_case", request_body="<REQUEST/>"), admin, db)
    plan = create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=api_row["id"], name="sm3 encrypt plan", items=[case_row["id"]]), admin, db)
    task = ExecutionTask(executor_id=admin.id, project_id=project["id"], environment_id=environment["id"], target_type="plan", target_id=plan["id"], status="running")
    db.add(task)
    db.commit()
    db.refresh(task)

    rows = _execute(db, task)

    assert rows[0].status == "error"
    assert "SM3尾部签名不能与请求 Body 加密同时启用" in rows[0].error_message


def test_execute_plan_uses_environment_per_plan_item(db_session, monkeypatch):
    db, admin = db_session
    project = create_project(ProjectIn(name="plan_item_env_project", description="plan item env"), admin, db)
    first_env = create_environment(EnvironmentIn(project_id=project["id"], name="first_env", protocol="https", base_url="first.example.com", variables={"envName": "first"}), admin, db)
    second_env = create_environment(EnvironmentIn(project_id=project["id"], name="second_env", protocol="https", base_url="second.example.com", variables={"envName": "second"}), admin, db)
    api_row = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=first_env["id"], name="env_api", method="POST", path="/submit"), admin, db)
    first_case = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="first_env_case", request_body={"env": "${envName}"}), admin, db)
    second_case = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="second_env_case", request_body={"env": "${envName}"}), admin, db)
    plan = create_plan(
        TestPlanIn(
            project_id=project["id"],
            environment_id=first_env["id"],
            api_id=api_row["id"],
            name="plan item env",
            items=[
                {"case_id": first_case["id"], "environment_id": first_env["id"]},
                {"case_id": second_case["id"], "environment_id": second_env["id"]},
            ],
        ),
        admin,
        db,
    )
    task = ExecutionTask(executor_id=admin.id, project_id=project["id"], environment_id=first_env["id"], target_type="plan", target_id=plan["id"], status="running")
    db.add(task)
    db.commit()
    db.refresh(task)
    requests = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, headers=None, params=None, json=None):
            requests.append({"url": url, "json": json})
            return executor_service.httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(executor_service.httpx, "Client", FakeClient)

    rows = _execute(db, task)

    assert [row.status for row in rows] == ["passed", "passed"]
    assert requests == [
        {"url": "https://first.example.com/submit", "json": {"env": "first"}},
        {"url": "https://second.example.com/submit", "json": {"env": "second"}},
    ]


def test_execute_plan_uses_latest_upstream_value_for_duplicate_variable_names(db_session, monkeypatch):
    db, admin = db_session
    project = create_project(ProjectIn(name="dependency_duplicate_project", description="dependency project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    first_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="first_token_api", method="POST", path="/first-token"), admin, db)
    second_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="second_token_api", method="POST", path="/second-token"), admin, db)
    submit_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="duplicate_submit_api", method="POST", path="/submit"), admin, db)
    first_case = create_case(TestCaseIn(project_id=project["id"], api_id=first_api["id"], name="first_token_case", extractors=[{"name": "token", "path": "$.data.token"}]), admin, db)
    second_case = create_case(TestCaseIn(project_id=project["id"], api_id=second_api["id"], name="second_token_case", extractors=[{"name": "token", "path": "$.data.token"}]), admin, db)
    submit_case = create_case(TestCaseIn(project_id=project["id"], api_id=submit_api["id"], name="duplicate_submit_case", request_body={"token": "${token}"}), admin, db)
    plan = create_plan(
        TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=first_api["id"], name="duplicate dependency plan", items=[first_case["id"], second_case["id"], submit_case["id"]]),
        admin,
        db,
    )
    task = ExecutionTask(executor_id=admin.id, project_id=project["id"], environment_id=environment["id"], target_type="plan", target_id=plan["id"], status="running")
    db.add(task)
    db.commit()
    db.refresh(task)
    requests = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, headers=None, params=None, json=None):
            requests.append({"url": url, "json": json})
            if url.endswith("/first-token"):
                return executor_service.httpx.Response(200, json={"data": {"token": "first-token"}})
            if url.endswith("/second-token"):
                return executor_service.httpx.Response(200, json={"data": {"token": "second-token"}})
            return executor_service.httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(executor_service.httpx, "Client", FakeClient)

    _execute(db, task)

    assert requests[2]["json"] == {"token": "second-token"}


def test_execute_plan_extracts_plain_text_response_for_later_case(db_session, monkeypatch):
    db, admin = db_session
    project = create_project(ProjectIn(name="plain_text_dependency_project", description="dependency project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    token_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="plain_token_api", method="POST", path="/plain-token"), admin, db)
    submit_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="plain_submit_api", method="POST", path="/plain-submit"), admin, db)
    token_case = create_case(TestCaseIn(project_id=project["id"], api_id=token_api["id"], name="plain_token_case", extractors=[{"name": "plainToken", "source": "regex", "path": "(.+)"}]), admin, db)
    submit_case = create_case(TestCaseIn(project_id=project["id"], api_id=submit_api["id"], name="plain_submit_case", request_body={"token": "${plainToken}"}), admin, db)
    plan = create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=token_api["id"], name="plain text dependency plan", items=[token_case["id"], submit_case["id"]]), admin, db)
    task = ExecutionTask(executor_id=admin.id, project_id=project["id"], environment_id=environment["id"], target_type="plan", target_id=plan["id"], status="running")
    db.add(task)
    db.commit()
    db.refresh(task)
    requests = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, headers=None, params=None, json=None):
            requests.append({"url": url, "json": json})
            if url.endswith("/plain-token"):
                return executor_service.httpx.Response(200, text="STRING_TOKEN_001")
            return executor_service.httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(executor_service.httpx, "Client", FakeClient)

    rows = _execute(db, task)
    first_response = executor_service.parse_json(rows[0].response_snapshot_json, {})

    assert requests[1]["json"] == {"token": "STRING_TOKEN_001"}
    assert first_response["extracted_variables"] == [
        {"name": "plainToken", "path": "(.+)", "source": "regex", "value": "STRING_TOKEN_001", "success": True}
    ]


def test_executor_sends_body_by_api_body_format(db_session, monkeypatch):
    db, admin = db_session
    project = create_project(ProjectIn(name="body_format_project", description="body format project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    xml_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="xml_api", method="POST", path="/xml", body={"format": "xml"}), admin, db)
    form_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="form_api", method="POST", path="/form", body={"format": "x-www-form-data"}), admin, db)
    json_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="json_api", method="POST", path="/json", body={"format": "json"}), admin, db)
    xml_case = create_case(TestCaseIn(project_id=project["id"], api_id=xml_api["id"], name="xml_case", request_body="<request><name>${name}</name></request>"), admin, db)
    form_case = create_case(TestCaseIn(project_id=project["id"], api_id=form_api["id"], name="form_case", request_body={"name": "${name}"}), admin, db)
    json_case = create_case(TestCaseIn(project_id=project["id"], api_id=json_api["id"], name="json_case", request_body={"name": "${name}"}), admin, db)
    plan = create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=xml_api["id"], name="body format plan", items=[xml_case["id"], form_case["id"], json_case["id"]]), admin, db)
    task = ExecutionTask(executor_id=admin.id, project_id=project["id"], environment_id=environment["id"], target_type="plan", target_id=plan["id"], status="running")
    db.add(task)
    db.commit()
    db.refresh(task)
    requests = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, **kwargs):
            requests.append(kwargs)
            return executor_service.httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(executor_service.httpx, "Client", FakeClient)
    env = db.get(Environment, environment["id"])
    env.variables_json = executor_service.dump_json({"name": "格式演示"})
    db.commit()

    _execute(db, task)

    assert requests[0]["content"] == "<request><name>格式演示</name></request>"
    assert requests[1]["data"] == {"name": "格式演示"}
    assert requests[2]["json"] == {"name": "格式演示"}


def test_execution_reports_search_and_soft_delete(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="report_project", description="report project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    api_row = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="report_api", method="GET", path="/report"), admin, db)
    case_row = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="report_case"), admin, db)
    plan = create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=api_row["id"], name="nightly report plan", items=[case_row["id"]]), admin, db)
    task = execute_plan(plan["id"], admin, db)

    listed = list_executions(name="nightly", target_type="plan", page=1, page_size=10, _=admin, db=db)
    assert listed["total"] == 1
    assert listed["items"][0]["target_name"] == "nightly report plan"
    assert listed["items"][0]["project_name"] == "report_project"

    deleted = delete_execution(task["id"], admin, db)
    assert deleted["id"] == task["id"]
    assert list_executions(name="nightly", target_type="plan", page=1, page_size=10, _=admin, db=db)["total"] == 0


def test_log_center_operation_execution_exception_and_detail(db_session):
    db, admin = db_session
    project = create_project(ProjectIn(name="log_project", description="log project"), admin, db)
    environment = create_test_environment(project["id"], admin, db)
    api_row = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="log_api", method="POST", path="/log", body={"format": "json"}), admin, db)
    case_row = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="log_case"), admin, db)
    plan = create_plan(TestPlanIn(project_id=project["id"], environment_id=environment["id"], api_id=api_row["id"], name="log plan", items=[case_row["id"]]), admin, db)
    task = ExecutionTask(executor_id=admin.id, project_id=project["id"], environment_id=environment["id"], target_type="plan", target_id=plan["id"], status="failed")
    db.add(task)
    db.commit()
    db.refresh(task)
    result = ExecutionResult(
        task_id=task.id,
        case_id=case_row["id"],
        status="failed",
        request_snapshot_json=executor_service.dump_json({"method": "POST", "url": "http://example.test/log", "headers": {}, "query": {}, "body": {"name": "demo"}}),
        response_snapshot_json=executor_service.dump_json({"status_code": 200, "text": '{"code":1}', "duration_ms": 12, "extracted_variables": []}),
        assertion_results_json=executor_service.dump_json([{"type": "jsonpath_equal", "path": "$.code", "expected": 0, "actual": 1, "passed": False, "message": "failed"}]),
        duration_ms=12,
        error_message="",
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    operation_logs = list_logs(module="project", result="success", page=1, page_size=10, _=admin, db=db)
    assert operation_logs["total"] >= 1
    assert operation_logs["items"][0]["operator_name"]

    execution_logs = list_execution_logs(name="log", status="failed", task_id=task.id, page=1, page_size=10, _=admin, db=db)
    assert execution_logs["total"] == 1
    assert execution_logs["items"][0]["case_name"] == "log_case"

    log_system_exception(db, "POST", "/api/projects", "RuntimeError", "保存项目失败", "127.0.0.1")
    exception_logs = list_exception_logs(name="/api/projects", status="error", page=1, page_size=10, _=admin, db=db)
    assert exception_logs["total"] == 1
    assert exception_logs["items"][0]["module"] == "system"
    assert exception_logs["items"][0]["action"] == "exception"
    assert exception_logs["items"][0]["path"] == "/api/projects"
    assert exception_logs["items"][0]["error_type"] == "RuntimeError"
    assert exception_logs["items"][0]["error_message"] == "保存项目失败"

    detail = get_execution_log_detail(result.id, admin, db)
    assert detail["request_snapshot"]["body"] == {"name": "demo"}
    assert detail["response_snapshot"]["status_code"] == 200
    assert detail["assertion_results"][0]["expected"] == 0


def test_html_report_formats_request_and_response_payloads():
    class FakeTask:
        id = 7
        status = "failed"

    class FakeResult:
        case_id = 12
        case_name = "XML用例"
        api_name = "库存接口"
        status = "failed"
        duration_ms = 123
        assertion_results = [{"type": "xmlpath_equal", "path": ".//STATUS", "expected": "S", "actual": "F", "passed": False, "message": "失败"}]
        request_snapshot = {
            "method": "POST",
            "url": "http://example.test/api",
            "headers": {"Content-Type": "application/xml"},
            "query": {},
            "body": '<?xml version="1.0" encoding="UTF-8"?><RESPONSE><STATUS>F</STATUS><EMPTY>\n    </EMPTY></RESPONSE>SIGN',
        }
        response_snapshot = {
            "status_code": 200,
            "headers": {"Content-Type": "application/xml"},
            "text": '<?xml version="1.0" encoding="UTF-8"?><RESPONSE><STATUS>F</STATUS><EMPTY>\n    </EMPTY></RESPONSE>SIGN',
            "duration_ms": 123,
        }

    html = build_html_report(FakeTask(), [FakeResult()], "report")

    assert "请求报文" in html
    assert "响应报文" in html
    assert escape('<?xml version="1.0" encoding="UTF-8"?>') in html
    assert escape("<EMPTY/>") in html
    assert "期望" in html
    assert "实际" in html
