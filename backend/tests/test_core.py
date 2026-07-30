import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Environment, ExecutionTask, Project, TestCase as TestCaseModel, TestSuite, User
from app.routers.auth import change_password, login
from app.routers.crud import create_api, create_case, create_environment, create_plan, create_project, delete_api, delete_case, delete_environment, delete_plan, delete_project, execute_plan, list_apis, list_cases, list_environments, list_plans, list_projects, update_api, update_case, update_environment, update_plan, update_project
from app.routers.executions import delete_execution, list_executions
from app.routers.mock import router as mock_router
from app.routers.users import create_user, list_users, router as users_router, update_user, update_user_status
from app.schemas import ApiDefinitionIn, ApiDefinitionUpdate, ChangePasswordIn, EnvironmentIn, EnvironmentUpdate, LoginIn, ProjectIn, ProjectUpdate, TestCaseIn, TestCaseUpdate, TestPlanIn, TestPlanUpdate, UserCreate, UserStatusUpdate, UserUpdate
from app.services.assertions import all_passed, run_assertions
from app.services.executor import _build_request_url, _initial_variables
from app.services.jsonpath import find_jsonpath
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
    created = create_api(ApiDefinitionIn(project_id=project["id"], name="login", method="POST", path="/login", module="legacy", headers={"A": "B"}, query={"q": 1}, body={"x": 1}, description="login api"), admin, db)

    assert created["environment_id"] == 0
    assert created["environment_name"] == ""
    assert created["module"] == ""
    assert created["headers"] == {"A": "B"}
    assert created["query"] == {"q": 1}
    assert created["body"] == {"x": 1}
    assert created["description"] == "login api"

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
            body={"format": "json"},
            description="new description",
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
    assert updated["body"] == {"format": "json"}
    assert updated["description"] == "new description"

    with pytest.raises(HTTPException) as duplicate_error:
        update_api(first["id"], ApiDefinitionUpdate(project_id=second_project["id"], environment_id=second_environment["id"], name="duplicate_api", method="GET", path="/dup2"), admin, db)
    assert duplicate_error.value.status_code == 400

    historical_update = update_api(first["id"], ApiDefinitionUpdate(project_id=first_project["id"], environment_id=second_environment["id"], name="historical_env_update", method="GET", path="/historical-env"), admin, db)
    assert historical_update["environment_id"] == second_environment["id"]


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
            priority="P1",
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
            priority="P2",
        ),
        admin,
        db,
    )

    assert created["project_name"] == "case_project_first"
    assert created["api_name"] == "case_api_first"
    assert created["request_body"] == {"username": "tester"}
    assert created["priority"] == "P1"
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
    assert second_project_paged["items"][0]["assertions"] == [{"type": "body_contains", "path": "", "operator": "==", "expected": "ok"}]

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
            assertions=[{"type": "jsonpath_equal", "path": "$.code", "operator": "==", "expected": 0}],
            tags="updated description",
            priority="P0",
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
    assert updated["assertions"] == [{"type": "jsonpath_equal", "path": "$.code", "operator": "==", "expected": 0}]
    assert updated["tags"] == "updated description"
    assert updated["priority"] == "P0"
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
    other_environment = create_test_environment(other_project["id"], admin, db)
    api_row = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="plan_api", method="POST", path="/plan"), admin, db)
    same_project_other_api = create_api(ApiDefinitionIn(project_id=project["id"], environment_id=environment["id"], name="plan_token_api", method="POST", path="/token"), admin, db)
    other_api = create_api(ApiDefinitionIn(project_id=other_project["id"], environment_id=other_environment["id"], name="other_plan_api", method="GET", path="/other"), admin, db)
    first_case = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="first_plan_case", priority="P0"), admin, db)
    second_case = create_case(TestCaseIn(project_id=project["id"], api_id=api_row["id"], name="second_plan_case", priority="P2"), admin, db)
    token_case = create_case(TestCaseIn(project_id=project["id"], api_id=same_project_other_api["id"], name="token_plan_case", priority="P1"), admin, db)
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
    assert created["items"] == [first_case["id"], second_case["id"]]
    assert [item["name"] for item in created["cases"]] == ["first_plan_case", "second_plan_case"]
    assert created["creator_name"] == "Admin"

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
            items=[first_case["id"], token_case["id"]],
        ),
        admin,
        db,
    )
    assert mixed_api_plan["items"] == [first_case["id"], token_case["id"]]
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
    assert updated["items"] == [second_case["id"], first_case["id"]]

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
