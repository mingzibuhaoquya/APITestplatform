from datetime import datetime
import base64
import re
import time
from urllib.parse import urljoin, urlparse
from uuid import uuid4
import httpx
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models import ApiDefinition, Environment, ExecutionResult, ExecutionTask, ScenarioCase, TestCase, TestSuite
from ..utils import dump_json, parse_json
from .assertions import all_passed, run_assertions
from .crypto_envelope import CryptoEnvelopeError, decrypt_body, encrypt_body, normalize_config
from .jsonpath import find_jsonpath
from .pre_scripts import PreScriptError, run_pre_script
from .report import build_html_report
from .variables import render_variables, response_json_or_text
from .xmlpath import find_xmlpath


class ResultView:
    def __init__(self, row: ExecutionResult, db: Session):
        case = db.get(TestCase, row.case_id) if row.case_id else None
        api = db.get(ApiDefinition, case.api_id) if case else None
        self.case_id = row.case_id
        self.case_name = case.name if case else ""
        self.api_name = api.name if api else ""
        self.status = row.status
        self.duration_ms = row.duration_ms
        self.request_snapshot = parse_json(row.request_snapshot_json, {})
        self.response_snapshot = parse_json(row.response_snapshot_json, {})
        self.assertion_results = parse_json(row.assertion_results_json, [])


def execute_task(task_id: int) -> None:
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        task = db.get(ExecutionTask, task_id)
        if not task:
            return
        task.status = "running"
        task.started_at = datetime.now()
        _sync_plan_execution(db, task)
        db.commit()
        rows = _execute(db, task)
        passed = sum(1 for row in rows if row.status == "passed")
        failed = len(rows) - passed
        task.status = "passed" if failed == 0 else "failed"
        task.ended_at = datetime.now()
        task.summary_json = dump_json({"total": len(rows), "passed": passed, "failed": failed})
        task.report_html = build_html_report(task, [ResultView(row, db) for row in rows], _execution_target_name(db, task))
        _sync_plan_execution(db, task)
        db.commit()
    except Exception as exc:
        db.rollback()
        task = db.get(ExecutionTask, task_id)
        if task:
            task.status = "error"
            task.ended_at = datetime.now()
            task.summary_json = dump_json({"error": str(exc)})
            _sync_plan_execution(db, task)
            db.commit()
    finally:
        db.close()


def _execute(db: Session, task: ExecutionTask) -> list[ExecutionResult]:
    if task.target_type == "case":
        case_ids = [task.target_id]
    elif task.target_type == "plan":
        plan = db.get(TestSuite, task.target_id)
        case_ids = parse_json(plan.items_json if plan else "[]", [])
    else:
        scenario = db.get(ScenarioCase, task.target_id)
        case_ids = parse_json(scenario.steps_json if scenario else "[]", [])
    variables = _initial_variables(db, task.environment_id)
    auth_token_cache: dict[str, str] = {}
    rows: list[ExecutionResult] = []
    for case_id in case_ids:
        row = _execute_case(db, task, int(case_id), variables, auth_token_cache)
        rows.append(row)
        if row.status != "passed" and task.target_type == "scenario":
            scenario = db.get(ScenarioCase, task.target_id)
            if scenario and scenario.failure_strategy == "stop":
                break
    return rows


def _sync_plan_execution(db: Session, task: ExecutionTask) -> None:
    if task.target_type != "plan":
        return
    plan = db.get(TestSuite, task.target_id)
    if not plan:
        return
    plan.last_execution_id = task.id
    plan.last_status = task.status
    plan.last_executed_at = task.ended_at or datetime.now()


def _execution_target_name(db: Session, task: ExecutionTask) -> str:
    if task.target_type == "plan":
        plan = db.get(TestSuite, task.target_id)
        return plan.name if plan else ""
    if task.target_type == "case":
        case = db.get(TestCase, task.target_id)
        return case.name if case else ""
    scenario = db.get(ScenarioCase, task.target_id)
    return scenario.name if scenario else ""


def _initial_variables(db: Session, environment_id: int) -> dict:
    env = db.get(Environment, environment_id)
    variables = parse_json(env.variables_json if env else "{}", {})
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    variables.setdefault("timestamp", timestamp)
    variables.setdefault("uuid", uuid4().hex)
    variables.setdefault("unique_username", f"test_user_{timestamp}")
    return variables


def _build_request_url(env: Environment, path: str) -> str:
    base_url = (env.base_url or "").strip().rstrip("/")
    if urlparse(base_url).scheme:
        root = base_url
    else:
        default_port = 80 if env.protocol == "http" else 443
        port = "" if env.port == default_port else f":{env.port}"
        root = f"{env.protocol}://{base_url.lstrip('/')}{port}"
    return urljoin(root.rstrip("/") + "/", path.lstrip("/"))


def _execute_case(db: Session, task: ExecutionTask, case_id: int, variables: dict, auth_token_cache: dict[str, str] | None = None) -> ExecutionResult:
    case = db.get(TestCase, case_id)
    env = db.get(Environment, task.environment_id)
    api = db.get(ApiDefinition, case.api_id) if case else None
    if not case or case.is_deleted or not api or not env:
        return _save_result(db, task.id, case_id, "error", {}, {}, [], 0, "用例、接口或环境不存在")

    env_headers = parse_json(env.headers_json, {})
    headers = {**env_headers, **parse_json(api.headers_json, {}), **parse_json(case.request_headers_json, {})}
    query = {**parse_json(api.query_json, {}), **parse_json(case.request_query_json, {})}
    body = parse_json(case.request_body_json, {})
    body_format = _request_body_format(api)
    url = _build_request_url(env, api.path)
    try:
        script_logs = run_pre_script(api.pre_script, variables, headers)
    except PreScriptError as exc:
        return _save_result(
            db,
            task.id,
            case_id,
            "error",
            {"pre_script_logs": [], "pre_script_error": str(exc)},
            {},
            [],
            0,
            f"Pre-script execution failed: {exc}",
        )
    rendered_headers = render_variables(headers, variables)
    rendered_query = render_variables(query, variables)
    rendered_body = render_variables(body, variables)
    auth_config = parse_json(api.auth_config_json, {"type": "none"})
    try:
        _apply_auth_config(
            auth_config,
            env,
            api.path,
            rendered_headers,
            rendered_query,
            variables,
            auth_token_cache if auth_token_cache is not None else {},
        )
    except Exception as exc:
        return _save_result(
            db,
            task.id,
            case_id,
            "error",
            {"method": api.method, "url": render_variables(url, variables), "headers": rendered_headers, "query": rendered_query, "auth_error": str(exc)},
            {},
            [],
            0,
            f"Authorization failed: {exc}",
        )
    encryption = normalize_config(parse_json(api.encryption_config_json, {}))
    sent_body = rendered_body
    try:
        if encryption["encrypt_request"]:
            sent_body = encrypt_body(rendered_body, rendered_headers, encryption)
    except CryptoEnvelopeError as exc:
        return _save_result(
            db, task.id, case_id, "error",
            {"method": api.method, "url": render_variables(url, variables), "headers": rendered_headers, "body_original": rendered_body, "encryption_error": str(exc)},
            {}, [], 0, f"Request encryption failed: {exc}",
        )
    request_snapshot = {
        "method": api.method,
        "url": render_variables(url, variables),
        "headers": rendered_headers,
        "query": rendered_query,
        "body": sent_body,
        "pre_script_logs": script_logs,
    }
    if encryption["encrypt_request"]:
        request_snapshot["body_original"] = rendered_body

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=30) as client:
            response = _send_request(client, request_snapshot, body_format)
        duration_ms = int((time.perf_counter() - started) * 1000)
        text = response.text[: get_settings().response_body_limit]
        parsed = response_json_or_text(text)
        response_snapshot = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "text": text,
            "json": parsed if not isinstance(parsed, str) else None,
            "duration_ms": duration_ms,
        }
        if encryption["decrypt_response"]:
            try:
                decrypted_text, decrypted_json = decrypt_body(parsed, encryption)
            except CryptoEnvelopeError as exc:
                response_snapshot["decryption_error"] = str(exc)
                return _save_result(db, task.id, case_id, "error", request_snapshot, response_snapshot, [], duration_ms, f"Response decryption failed: {exc}")
            response_snapshot["encrypted_json"] = parsed
            response_snapshot["decrypted_text"] = decrypted_text
            response_snapshot["decrypted_json"] = decrypted_json
            response_snapshot["json"] = decrypted_json
        assertion_results = run_assertions(response_snapshot, parse_json(case.assertions_json, []))
        response_snapshot["extracted_variables"] = _extract_variables(variables, response_snapshot, parse_json(case.extractors_json, []))
        status = "passed" if all_passed(assertion_results) else "failed"
        return _save_result(db, task.id, case_id, status, request_snapshot, response_snapshot, assertion_results, duration_ms, "")
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return _save_result(db, task.id, case_id, "error", request_snapshot, {}, [], duration_ms, str(exc))


def _extract_variables(variables: dict, response_snapshot: dict, extractors: list[dict]) -> list[dict]:
    body = response_snapshot.get("json") or response_snapshot.get("text")
    text = str(response_snapshot.get("text") or "")
    results = []
    for item in extractors:
        name = str(item.get("name") or "").strip()
        path = str(item.get("path") or "").strip()
        source = str(item.get("source") or "jsonpath").strip()
        values = _extract_values(source, body, text, path)
        success = bool(name and values and (source == "text" or path))
        value = values[0] if success else None
        if success:
            variables[name] = value
        results.append({"name": name, "path": path, "source": source, "value": value, "success": success})
    return results


def _extract_values(source: str, body: object, text: str, path: str) -> list:
    if source == "regex":
        if not path:
            return []
        match = re.search(path, text, re.S)
        if not match:
            return []
        return [match.group(1) if match.groups() else match.group(0)]
    if source == "xmlpath":
        return find_xmlpath(text, path)
    return find_jsonpath(body, path)


def _request_body_format(api: ApiDefinition) -> str:
    body_config = parse_json(api.body_json, {})
    body_format = body_config.get("format") if isinstance(body_config, dict) else ""
    return body_format if body_format in {"json", "xml", "x-www-form-data"} else "json"


def _send_request(client: httpx.Client, request_snapshot: dict, body_format: str) -> httpx.Response:
    body = request_snapshot["body"]
    common = {
        "method": request_snapshot["method"],
        "url": request_snapshot["url"],
        "headers": request_snapshot["headers"],
        "params": request_snapshot["query"],
    }
    if body in ({}, "", None):
        return client.request(**common)
    if body_format == "xml":
        return client.request(**common, content=str(body))
    if body_format == "x-www-form-data":
        return client.request(**common, data=body if isinstance(body, dict) else str(body))
    return client.request(**common, json=body)


def _save_result(
    db: Session,
    task_id: int,
    case_id: int | None,
    status: str,
    request_snapshot: dict,
    response_snapshot: dict,
    assertion_results: list[dict],
    duration_ms: int,
    error_message: str,
) -> ExecutionResult:
    row = ExecutionResult(
        task_id=task_id,
        case_id=case_id,
        status=status,
        request_snapshot_json=dump_json(request_snapshot),
        response_snapshot_json=dump_json(response_snapshot),
        assertion_results_json=dump_json(assertion_results),
        duration_ms=duration_ms,
        error_message=error_message,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _auth_header_exists(headers: dict, header_name: str) -> bool:
    return any(str(key).lower() == header_name.lower() for key in headers)


def _default_token_url(env: Environment) -> str:
    return urljoin(_build_request_url(env, "/").rstrip("/") + "/", "OAuth/Oauth/Token")


def _token_cache_key(auth: dict, env: Environment, variables: dict) -> str:
    key_data = {
        "token_url": render_variables(auth.get("token_url") or _default_token_url(env), variables),
        "client_id": render_variables(auth.get("client_id", ""), variables),
        "scope": render_variables(auth.get("scope", ""), variables),
        "audience": render_variables(auth.get("audience", ""), variables),
        "client_authentication": auth.get("client_authentication", "body"),
    }
    return dump_json(key_data)


def _request_oauth2_client_credentials_token(auth: dict, env: Environment, request_url: str, variables: dict) -> str:
    token_url = render_variables(auth.get("token_url") or _default_token_url(env), variables)
    client_id = render_variables(auth.get("client_id", ""), variables)
    client_secret = render_variables(auth.get("client_secret", ""), variables)
    scope = render_variables(auth.get("scope") or request_url, variables)
    audience = render_variables(auth.get("audience", ""), variables)
    if not token_url:
        raise ValueError("OAuth2 token URL is required")
    if not client_id:
        raise ValueError("OAuth2 client ID is required")
    data = {
        "grant_type": "client_credentials",
        "scope": scope,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    auth_param = None
    if auth.get("client_authentication") == "basic":
        auth_param = (client_id, client_secret)
    else:
        data["client_id"] = client_id
        data["client_secret"] = client_secret
    if audience:
        data["audience"] = audience
    with httpx.Client(timeout=30) as client:
        response = client.post(token_url, data=data, headers=headers, auth=auth_param)
    if response.status_code >= 400:
        raise ValueError(f"OAuth2 token request failed with status {response.status_code}")
    payload = response_json_or_text(response.text)
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise ValueError("OAuth2 token response does not contain access_token")
    return str(payload["access_token"])


def _apply_auth_config(auth: dict, env: Environment, path: str, headers: dict, query: dict, variables: dict, token_cache: dict[str, str]) -> None:
    auth_type = auth.get("type", "none")
    if auth_type in ("", "none"):
        return
    header_name = str(auth.get("header_name") or "Authorization")
    header_prefix = str(auth.get("header_prefix") or "Bearer").strip()
    if auth_type == "bearer":
        token = render_variables(auth.get("token", ""), variables)
        if token and not _auth_header_exists(headers, header_name):
            headers[header_name] = f"{header_prefix} {token}".strip()
        return
    if auth_type == "basic":
        username = render_variables(auth.get("username", ""), variables)
        password = render_variables(auth.get("password", ""), variables)
        raw = f"{username}:{password}".encode("utf-8")
        if not _auth_header_exists(headers, header_name):
            headers[header_name] = "Basic " + base64.b64encode(raw).decode("ascii")
        return
    if auth_type == "api_key":
        key = str(auth.get("api_key_name") or "").strip()
        value = render_variables(auth.get("api_key_value", ""), variables)
        if key and value:
            if auth.get("add_to") == "query":
                query.setdefault(key, value)
            elif not _auth_header_exists(headers, key):
                headers[key] = value
        return
    if auth_type == "oauth2_client_credentials":
        request_url = render_variables(_build_request_url(env, path), variables)
        cache_key = _token_cache_key(auth, env, variables)
        token = token_cache.get(cache_key)
        if not token:
            token = _request_oauth2_client_credentials_token(auth, env, request_url, variables)
            token_cache[cache_key] = token
        if auth.get("add_to") == "query":
            query.setdefault("access_token", token)
        elif not _auth_header_exists(headers, header_name):
            headers[header_name] = f"{header_prefix} {token}".strip()


def get_oauth2_preview_token(auth: dict, env: Environment, path: str, variables: dict) -> str:
    request_url = render_variables(_build_request_url(env, path), variables)
    return _request_oauth2_client_credentials_token(auth, env, request_url, variables)
