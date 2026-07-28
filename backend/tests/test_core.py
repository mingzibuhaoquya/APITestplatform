import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import User
from app.routers.auth import change_password, login
from app.routers.users import create_user, list_users, router as users_router, update_user, update_user_status
from app.schemas import ChangePasswordIn, LoginIn, UserCreate, UserStatusUpdate, UserUpdate
from app.services.assertions import all_passed, run_assertions
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


def test_render_variables_nested():
    payload = {"headers": {"Authorization": "Bearer ${token}"}, "ids": ["${user_id}"]}
    assert render_variables(payload, {"token": "abc", "user_id": 12}) == {
        "headers": {"Authorization": "Bearer abc"},
        "ids": ["12"],
    }


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
