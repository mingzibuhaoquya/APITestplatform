import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy.orm import Session

from ..models import AiSetting, Environment, ExecutionResult, ExecutionTask, UiExecutionArtifact, UiTestCase
from ..utils import dump_json, parse_json
from .report import build_html_report


ARTIFACT_ROOT = Path("logs/ui-artifacts")
DEFAULT_UI_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
DEFAULT_UI_LOCALE = "zh-CN"


class UiResultView:
    def __init__(self, row: ExecutionResult, case: UiTestCase | None):
        self.case_id = row.case_id
        self.case_name = case.name if case else ""
        self.api_name = "UI自动化"
        self.status = row.status
        self.duration_ms = row.duration_ms
        self.request_snapshot = parse_json(row.request_snapshot_json, {})
        self.response_snapshot = parse_json(row.response_snapshot_json, {})
        self.assertion_results = parse_json(row.assertion_results_json, [])


def build_ui_url(env: Environment, start_url: str) -> str:
    value = (start_url or "").strip()
    if urlparse(value).scheme:
        return value
    base_url = (env.base_url or "").strip().rstrip("/")
    if urlparse(base_url).scheme:
        root = base_url
    else:
        default_port = 80 if env.protocol == "http" else 443
        port = "" if env.port == default_port else f":{env.port}"
        root = f"{env.protocol}://{base_url}{port}"
    return urljoin(root + "/", value.lstrip("/"))


def _ui_wait_until(case: UiTestCase) -> str:
    value = str(getattr(case, "wait_until", "") or "networkidle")
    return value if value in {"domcontentloaded", "load", "networkidle"} else "networkidle"


def _ui_wait_after_load_ms(case: UiTestCase) -> int:
    try:
        return min(max(int(getattr(case, "wait_after_load_ms", 500) or 0), 0), 60000)
    except (TypeError, ValueError):
        return 500


def _goto_and_wait(page, destination: str, case: UiTestCase) -> None:
    page.goto(destination, wait_until=_ui_wait_until(case), timeout=60000)
    wait_ms = _ui_wait_after_load_ms(case)
    if wait_ms:
        page.wait_for_timeout(wait_ms)


def execute_ui_task(task_id: int) -> None:
    from ..database import SessionLocal
    from .ui_agent_executor import execute_ui_agent_case

    db = SessionLocal()
    try:
        task = db.get(ExecutionTask, task_id)
        if not task:
            return
        task.status = "running"
        task.started_at = datetime.now()
        db.commit()

        case = db.get(UiTestCase, task.target_id)
        row = execute_ui_agent_case(db, task) if case and case.execution_mode == "ai" else _execute_ui_case(db, task)
        task.status = "passed" if row.status == "passed" else "failed"
        task.ended_at = datetime.now()
        task.summary_json = dump_json({"total": 1, "passed": 1 if row.status == "passed" else 0, "failed": 0 if row.status == "passed" else 1})
        case = db.get(UiTestCase, row.case_id) if row.case_id else case
        task.report_html = build_html_report(task, [UiResultView(row, case)], case.name if case else "")
        db.commit()
    except Exception as exc:
        db.rollback()
        task = db.get(ExecutionTask, task_id)
        if task:
            task.status = "error"
            task.ended_at = datetime.now()
            task.summary_json = dump_json({"error": str(exc)})
            db.commit()
    finally:
        db.close()


def _execute_ui_case(db: Session, task: ExecutionTask) -> ExecutionResult:
    case = db.get(UiTestCase, task.target_id)
    env = db.get(Environment, task.environment_id)
    if not case or case.is_deleted or not env:
        return _save_result(db, task.id, task.target_id, "error", {}, {"steps": []}, [], 0, "UI用例或环境不存在")
    steps = parse_json(case.steps_json, [])
    started = time.perf_counter()
    step_results: list[dict] = []
    assertions: list[dict] = []
    screenshots: list[dict] = []
    current_url = ""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        message = f"Playwright未安装或浏览器依赖缺失: {exc}"
        return _save_result(db, task.id, case.id, "error", {"browser": "chromium", "headless": getattr(case, "headless", True) is not False, "user_agent": DEFAULT_UI_USER_AGENT, "locale": DEFAULT_UI_LOCALE, "wait_until": _ui_wait_until(case), "wait_after_load_ms": _ui_wait_after_load_ms(case), "start_url": case.start_url, "steps": steps}, {"steps": step_results}, [], duration_ms, message)

    try:
        with sync_playwright() as playwright:
            headless = getattr(case, "headless", True) is not False
            browser = playwright.chromium.launch(headless=headless)
            page = browser.new_page(
                user_agent=DEFAULT_UI_USER_AGENT,
                locale=DEFAULT_UI_LOCALE,
                viewport={"width": 1600, "height": 900},
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            )
            try:
                if case.start_url:
                    current_url = build_ui_url(env, case.start_url)
                    _goto_and_wait(page, current_url, case)
                for index, step in enumerate(steps, start=1):
                    result = _run_step(db, page, step, index, task.id, case)
                    step_results.append(result)
                    if result.get("screenshot"):
                        screenshots.append(result["screenshot"])
                    if result["status"] != "passed":
                        failure = _save_failure_screenshot(page, task.id, index)
                        if failure:
                            result["screenshot"] = failure
                            screenshots.append(failure)
                        break
            finally:
                browser.close()
    except (PlaywrightError, PlaywrightTimeoutError, Exception) as exc:
        step_results.append({"index": len(step_results) + 1, "status": "error", "message": str(exc)})

    duration_ms = int((time.perf_counter() - started) * 1000)
    passed = bool(step_results) and all(item["status"] == "passed" for item in step_results)
    for item in step_results:
        if item.get("assertion"):
            assertions.append(item["assertion"])
    row = _save_result(
        db,
        task.id,
        case.id,
        "passed" if passed else "failed",
        {"browser": "chromium", "headless": getattr(case, "headless", True) is not False, "user_agent": DEFAULT_UI_USER_AGENT, "locale": DEFAULT_UI_LOCALE, "wait_until": _ui_wait_until(case), "wait_after_load_ms": _ui_wait_after_load_ms(case), "start_url": current_url or case.start_url, "steps": steps},
        {"steps": step_results, "screenshots": screenshots},
        assertions,
        duration_ms,
        "" if passed else _first_error(step_results),
    )
    _save_artifacts(db, task.id, row.id, screenshots)
    return row


def _locator(page, step: dict, db: Session | None = None):
    locator_type = str(step.get("locator_type") or "css")
    target = str(step.get("target") or "")
    if locator_type == "ai":
        resolved = _resolve_ai_locator(db, page, step)
        if not resolved:
            raise RuntimeError("AI定位失败：未能根据描述匹配到可操作元素")
        next_step = {**step, "locator_type": resolved["locator_type"], "target": resolved["target"]}
        locator, _ = _locator(page, next_step)
        return locator, resolved
    if locator_type == "text":
        return page.get_by_text(target), None
    if locator_type == "xpath":
        return page.locator(f"xpath={target}"), None
    if locator_type == "placeholder":
        return page.get_by_placeholder(target), None
    if locator_type == "role":
        return page.get_by_role("button", name=target), None
    return page.locator(target), None


def _run_step(db: Session, page, step: dict, index: int, task_id: int, case: UiTestCase) -> dict:
    action = str(step.get("action") or "")
    value = str(step.get("value") or "")
    result = {"index": index, "action": action, "target": step.get("target", ""), "status": "passed", "message": "通过"}
    try:
        if action == "goto":
            destination = value or str(step.get("target") or "")
            if destination:
                _goto_and_wait(page, destination, case)
            else:
                result["message"] = "未填写地址，已保持当前页面"
        elif action == "click":
            locator, ai_locator = _locator(page, step, db)
            if ai_locator:
                result["ai_locator"] = ai_locator
            locator.click()
        elif action == "fill":
            locator, ai_locator = _locator(page, step, db)
            if ai_locator:
                result["ai_locator"] = ai_locator
            locator.fill(value)
        elif action == "select":
            locator, ai_locator = _locator(page, step, db)
            if ai_locator:
                result["ai_locator"] = ai_locator
            selected = False
            try:
                locator.select_option(value)
                selected = True
            except Exception:
                try:
                    locator.select_option(label=value)
                    selected = True
                except Exception as exc:
                    options = _select_options(locator)
                    suffix = f"；当前可选项：{options}" if options else "；当前下拉框没有可用选项"
                    raise RuntimeError(f"选择下拉项失败，期望值：{value}{suffix}") from exc
            if selected:
                locator.dispatch_event("input")
                locator.dispatch_event("change")
                locator.dispatch_event("blur")
        elif action == "wait":
            wait_text = value or str(step.get("target") or "")
            wait_target = str(step.get("target") or "").strip()
            locator_type = str(step.get("locator_type") or "")
            should_wait_for_element = (
                wait_target
                and not _is_generic_wait_text(wait_target)
                and not str(wait_text).isdigit()
                and locator_type in {"css", "xpath", "text", "placeholder", "role", "ai"}
            )
            if should_wait_for_element:
                locator, ai_locator = _locator(page, step, db)
                if ai_locator:
                    result["ai_locator"] = ai_locator
                locator.first.wait_for(state="visible", timeout=60000)
            else:
                try:
                    timeout_ms = int(value) if value.strip() else 1000
                except ValueError:
                    timeout_ms = 1000
                    result["message"] = "等待描述未匹配到具体元素，已按默认 1000ms 等待"
                page.wait_for_timeout(max(timeout_ms, 0))
        elif action == "assert_text":
            if str(step.get("locator_type") or "") == "ai":
                locator, ai_locator = _locator(page, step, db)
                if ai_locator:
                    result["ai_locator"] = ai_locator
                visible = locator.first.is_visible()
                path = ai_locator["target"] if ai_locator else step.get("target", "")
            else:
                visible = page.get_by_text(value or str(step.get("target") or "")).first().is_visible()
                path = value or step.get("target", "")
            result["assertion"] = {"type": "ui_assert_text", "path": path, "expected": "可见", "actual": "可见" if visible else "不可见", "passed": visible, "message": "通过" if visible else "未找到文本"}
            if not visible:
                result["status"] = "failed"
                result["message"] = "未找到文本"
        elif action == "assert_visible":
            locator, ai_locator = _locator(page, step, db)
            if ai_locator:
                result["ai_locator"] = ai_locator
            visible = locator.first.is_visible()
            result["assertion"] = {"type": "ui_assert_visible", "path": ai_locator["target"] if ai_locator else step.get("target", ""), "expected": "可见", "actual": "可见" if visible else "不可见", "passed": visible, "message": "通过" if visible else "元素不可见"}
            if not visible:
                result["status"] = "failed"
                result["message"] = "元素不可见"
        elif action == "screenshot":
            screenshot = _save_screenshot(page, task_id, index)
            result["screenshot"] = screenshot
        else:
            result["status"] = "failed"
            result["message"] = f"不支持的动作: {action}"
    except Exception as exc:
        result["status"] = "error"
        result["message"] = str(exc)
    return result


def _select_options(locator) -> list[dict]:
    try:
        return locator.evaluate(
            """(select) => Array.from(select.options || []).map(option => ({
                value: option.value,
                label: option.label || option.textContent.trim()
            }))"""
        )
    except Exception:
        return []


def _is_generic_wait_text(value: str) -> bool:
    compact = _normalize_text(value)
    return any(keyword in compact for keyword in ("等待界面", "等待页面", "等待加载", "加载完成", "加载成功"))


def _resolve_ai_locator(db: Session | None, page, step: dict) -> dict | None:
    candidates = _page_element_candidates(page)
    model_locator = _ai_locator_from_model(db, page, step, candidates)
    if model_locator:
        return model_locator
    return _local_ai_locator_from_candidates(step, candidates)


def _page_element_candidates(page) -> list[dict]:
    script = """
    () => {
      const clean = (value) => String(value || '').replace(/\\s+/g, ' ').trim().slice(0, 100);
      const selector = 'button,a,input,textarea,select,[role],[aria-label],[placeholder],label,[data-testid],[id],[name]';
      const elements = Array.from(document.querySelectorAll(selector));
      const items = [];
      for (const el of elements) {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        const visible = rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
        if (!visible) continue;
        items.push({
          tag: clean(el.tagName).toLowerCase(),
          text: clean(el.innerText || el.textContent || el.value),
          placeholder: clean(el.getAttribute('placeholder')),
          aria: clean(el.getAttribute('aria-label')),
          role: clean(el.getAttribute('role')),
          id: clean(el.id),
          name: clean(el.getAttribute('name')),
          dataTestId: clean(el.getAttribute('data-testid')),
          type: clean(el.getAttribute('type'))
        });
        if (items.length >= 80) break;
      }
      return items;
    }
    """
    try:
        candidates = page.evaluate(script)
        return candidates if isinstance(candidates, list) else []
    except Exception:
        return []


def _ai_locator_from_model(db: Session | None, page, step: dict, candidates: list[dict]) -> dict | None:
    if not db:
        return None
    setting = db.query(AiSetting).first()
    if not setting or setting.status != "active" or not setting.provider_url or not setting.model_name:
        return None

    user_prompt = {
        "action": step.get("action", ""),
        "target": step.get("target", ""),
        "value": step.get("value", ""),
        "description": step.get("description", ""),
        "page_url": getattr(page, "url", ""),
        "page_title": page.title(),
        "candidates": candidates,
    }
    payload = {
        "model": setting.model_name,
        "messages": [
            {
                "role": "system",
                "content": "你是Web UI自动化元素定位助手。只能返回JSON，格式为 {\"locator_type\":\"text|css|xpath|placeholder|role\", \"target\":\"定位内容\"}。优先选择稳定、可读、唯一的定位方式。",
            },
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json"}
    if setting.api_key:
        headers["Authorization"] = f"Bearer {setting.api_key}"
    try:
        response = httpx.post(_chat_completions_url(setting.provider_url), json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        locator = _extract_ai_locator_response(content)
        if locator:
            locator["source"] = "ai"
            return locator
    except Exception:
        return None
    return None


def _chat_completions_url(provider_url: str) -> str:
    value = (provider_url or "").strip().rstrip("/")
    if value.endswith("/chat/completions"):
        return value
    return f"{value}/chat/completions"


def _extract_ai_locator_response(content: str) -> dict | None:
    text = (content or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    locator_type = str(data.get("locator_type") or data.get("type") or "").strip()
    target = str(data.get("target") or data.get("selector") or data.get("locator") or "").strip()
    if locator_type not in {"text", "css", "xpath", "placeholder", "role"} or not target:
        return None
    return {"locator_type": locator_type, "target": target}


def _local_ai_locator_from_candidates(step: dict, candidates: list[dict]) -> dict | None:
    desired = _normalize_text(" ".join(str(step.get(key) or "") for key in ("target", "description", "value")))
    if not desired:
        return None
    for candidate in candidates:
        text = str(candidate.get("text") or "")
        if text and _matches_description(text, desired):
            if candidate.get("tag") == "button" or candidate.get("role") == "button":
                return {"locator_type": "role", "target": text, "source": "local"}
            return {"locator_type": "text", "target": text, "source": "local"}
    for candidate in candidates:
        placeholder = str(candidate.get("placeholder") or "")
        if placeholder and _matches_description(placeholder, desired):
            return {"locator_type": "placeholder", "target": placeholder, "source": "local"}
    for candidate in candidates:
        aria = str(candidate.get("aria") or "")
        if aria and _matches_description(aria, desired):
            return {"locator_type": "css", "target": _css_attr("aria-label", aria), "source": "local"}
    for candidate in candidates:
        label = _candidate_label(candidate)
        if not label or not _matches_description(label, desired):
            continue
        if candidate.get("dataTestId"):
            return {"locator_type": "css", "target": _css_attr("data-testid", str(candidate["dataTestId"])), "source": "local"}
        if candidate.get("id"):
            return {"locator_type": "css", "target": _css_id(str(candidate["id"])), "source": "local"}
        if candidate.get("name"):
            return {"locator_type": "css", "target": _css_attr("name", str(candidate["name"])), "source": "local"}
    return None


def _candidate_label(candidate: dict) -> str:
    for key in ("text", "placeholder", "aria", "name", "id"):
        value = str(candidate.get(key) or "")
        if value:
            return value
    return ""


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "").lower()


def _matches_description(label: str, normalized_desired: str) -> bool:
    normalized_label = _normalize_text(label)
    if not normalized_label:
        return False
    if normalized_label in normalized_desired or normalized_desired in normalized_label:
        return True
    for keyword in ("用户名", "用户", "账号", "密码", "验证码", "登录", "搜索", "查询", "提交", "保存", "确定", "取消", "关闭"):
        if keyword in normalized_label and keyword in normalized_desired:
            return True
    return False


def _css_attr(name: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'[{name}="{escaped}"]'


def _css_id(value: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", value):
        return f"#{value}"
    return _css_attr("id", value)


def _save_screenshot(page, task_id: int, step_index: int) -> dict:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_ROOT / f"task-{task_id}-step-{step_index}.png"
    page.screenshot(path=str(path), full_page=True)
    return {"step_index": step_index, "type": "screenshot", "path": str(path).replace("\\", "/")}


def _save_failure_screenshot(page, task_id: int, step_index: int) -> dict | None:
    try:
        ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        path = ARTIFACT_ROOT / f"task-{task_id}-step-{step_index}-failure.png"
        page.screenshot(path=str(path), full_page=True)
        return {"step_index": step_index, "type": "failure_screenshot", "path": str(path).replace("\\", "/")}
    except Exception:
        return None


def _first_error(steps: list[dict]) -> str:
    for item in steps:
        if item.get("status") != "passed":
            return str(item.get("message") or "UI步骤执行失败")
    return ""


def _save_artifacts(db: Session, task_id: int, result_id: int, screenshots: list[dict]) -> None:
    for item in screenshots:
        db.add(UiExecutionArtifact(task_id=task_id, result_id=result_id, step_index=int(item.get("step_index") or 0), artifact_type=str(item.get("type") or "screenshot"), file_path=str(item.get("path") or "")))
    db.commit()


def _save_result(db: Session, task_id: int, case_id: int | None, status: str, request_snapshot: dict, response_snapshot: dict, assertion_results: list[dict], duration_ms: int, error_message: str) -> ExecutionResult:
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
