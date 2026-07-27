from typing import Any
from .jsonpath import find_jsonpath


def _first(values: list[Any]) -> Any:
    return values[0] if values else None


def run_assertions(response: dict[str, Any], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    body = response.get("json", response.get("text", ""))
    for rule in rules:
        rule_type = rule.get("type")
        expected = rule.get("expected")
        path = rule.get("path", "")
        actual: Any = None
        passed = False
        message = ""

        if rule_type == "status_code":
            actual = response.get("status_code")
            passed = actual == int(expected)
        elif rule_type == "jsonpath_equal":
            values = find_jsonpath(body, path)
            actual = _first(values)
            passed = actual == expected
        elif rule_type == "jsonpath_exists":
            values = find_jsonpath(body, path)
            actual = _first(values)
            passed = bool(values)
        elif rule_type == "jsonpath_not_empty":
            values = find_jsonpath(body, path)
            actual = _first(values)
            passed = actual not in (None, "", [], {})
        elif rule_type == "duration_lt":
            actual = response.get("duration_ms")
            passed = int(actual) < int(expected)
        elif rule_type == "body_contains":
            actual = response.get("text", "")
            passed = str(expected) in actual
        else:
            message = f"未知断言类型: {rule_type}"

        if not message and not passed:
            message = f"断言失败，实际值: {actual}，期望值: {expected}"
        results.append({
            "type": rule_type,
            "path": path,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "message": message,
        })
    return results


def all_passed(results: list[dict[str, Any]]) -> bool:
    return all(item.get("passed") for item in results)

