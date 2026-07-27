from app.services.assertions import all_passed, run_assertions
from app.services.jsonpath import find_jsonpath
from app.services.variables import render_variables


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

