from datetime import datetime
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


class ResultView:
    def __init__(self, row: ExecutionResult):
        self.case_id = row.case_id
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
        task.report_html = build_html_report(task, [ResultView(row) for row in rows])
        _sync_plan_execution(db, task)
        db.commit()
    except Exception as exc:
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
    rows: list[ExecutionResult] = []
    for case_id in case_ids:
        row = _execute_case(db, task, int(case_id), variables)
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


def _execute_case(db: Session, task: ExecutionTask, case_id: int, variables: dict) -> ExecutionResult:
    case = db.get(TestCase, case_id)
    env = db.get(Environment, task.environment_id)
    api = db.get(ApiDefinition, case.api_id) if case else None
    if not case or case.is_deleted or not api or not env:
        return _save_result(db, task.id, case_id, "error", {}, {}, [], 0, "用例、接口或环境不存在")

    env_headers = parse_json(env.headers_json, {})
    headers = {**env_headers, **parse_json(api.headers_json, {}), **parse_json(case.request_headers_json, {})}
    query = {**parse_json(api.query_json, {}), **parse_json(case.request_query_json, {})}
    body = parse_json(case.request_body_json, {})
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
            response = client.request(
                request_snapshot["method"],
                request_snapshot["url"],
                headers=request_snapshot["headers"],
                params=request_snapshot["query"],
                json=request_snapshot["body"] if request_snapshot["body"] not in ({}, "", None) else None,
            )
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
        _extract_variables(variables, response_snapshot, parse_json(case.extractors_json, []))
        status = "passed" if all_passed(assertion_results) else "failed"
        return _save_result(db, task.id, case_id, status, request_snapshot, response_snapshot, assertion_results, duration_ms, "")
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return _save_result(db, task.id, case_id, "error", request_snapshot, {}, [], duration_ms, str(exc))


def _extract_variables(variables: dict, response_snapshot: dict, extractors: list[dict]) -> None:
    body = response_snapshot.get("json") or response_snapshot.get("text")
    for item in extractors:
        values = find_jsonpath(body, item.get("path", ""))
        if values:
            variables[item["name"]] = values[0]


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
