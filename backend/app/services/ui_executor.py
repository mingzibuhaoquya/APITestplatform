import json
import os
import random
import re
import string
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy.orm import Session

from ..models import AiSetting, Environment, ExecutionResult, ExecutionTask, Project, UiExecutionArtifact, UiTestCase, User
from ..utils import dump_json, parse_json
from .ai_settings import get_active_ai_setting
from .report import build_html_report


ARTIFACT_ROOT = Path("logs/ui-artifacts")
DEFAULT_UI_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
DEFAULT_UI_LOCALE = "zh-CN"
BROWSER_CHANNELS = {"chromium", "chrome", "msedge"}
UI_DYNAMIC_PATTERN = re.compile(r"\$\{random\.([A-Za-z_][A-Za-z0-9_]*)\(([^{}]*)\)\}")
VIN_CHARS = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"


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
        self.error_message = row.error_message


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


def _ui_browser_channel(case: UiTestCase) -> str:
    value = str(getattr(case, "browser_channel", "") or "chromium")
    return value if value in BROWSER_CHANNELS else "chromium"


def _ui_headless(case: UiTestCase) -> bool:
    headless = getattr(case, "headless", True) is not False
    if _ui_browser_channel(case) == "chromium" and os.name != "nt" and not os.environ.get("DISPLAY"):
        return True
    return headless


def _launch_ui_browser(playwright, case: UiTestCase):
    channel = _ui_browser_channel(case)
    headless = _ui_headless(case)
    options: dict[str, object] = {"headless": headless}
    if channel != "chromium":
        options["channel"] = channel
    try:
        return playwright.chromium.launch(**options)
    except Exception as exc:
        if channel == "chrome":
            raise RuntimeError("启动本机 Chrome 失败，请确认后端运行在本机环境且已安装 Chrome；Docker 容器内通常无法直接打开 Windows 桌面浏览器。") from exc
        if channel == "msedge":
            raise RuntimeError("启动本机 Edge 失败，请确认后端运行在本机环境且已安装 Microsoft Edge；Docker 容器内通常无法直接打开 Windows 桌面浏览器。") from exc
        raise


def _goto_and_wait(page, destination: str, case: UiTestCase) -> None:
    page.goto(destination, wait_until=_ui_wait_until(case), timeout=60000)
    _wait_for_page_ready(page, min(getattr(case, "step_timeout_ms", 10000) or 10000, 10000))
    wait_ms = _ui_wait_after_load_ms(case)
    if wait_ms:
        page.wait_for_timeout(wait_ms)
    _wait_for_page_ready(page, min(getattr(case, "step_timeout_ms", 10000) or 10000, 10000), "after_action")


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
        task.status = row.status if row.status in {"passed", "stopped"} else "failed"
        task.ended_at = datetime.now()
        task.summary_json = dump_json({
            "total": 1,
            "passed": 1 if row.status == "passed" else 0,
            "failed": 0 if row.status == "passed" else 1,
            "error": row.error_message or "",
        })
        case = db.get(UiTestCase, row.case_id) if row.case_id else case
        project = db.get(Project, task.project_id)
        environment = db.get(Environment, task.environment_id)
        executor = db.get(User, task.executor_id)
        task.project_name = project.name if project and not project.is_deleted else ""
        task.environment_name = environment.name if environment and not environment.is_deleted else ""
        task.executor_name = executor.real_name or executor.username if executor else ""
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
        return _save_result(db, task.id, case.id, "error", _ui_request_snapshot(case, env, case.start_url, steps), {"steps": step_results}, [], duration_ms, message)

    try:
        with sync_playwright() as playwright:
            browser = _launch_ui_browser(playwright, case)
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
                    if ui_task_stop_requested(db, task):
                        step_results.append({"index": index, "action": "stop", "status": "stopped", "message": "用户手动停止任务"})
                        break
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
    if passed and _needs_explicit_advanced_result(case, step_results):
        step_results.append(
            {
                "index": len(step_results) + 1,
                "action": "assert_result",
                "status": "failed",
                "message": "用例配置了期望结果，但最后没有明确断言或完成动作，不能仅凭截图判定通过。",
            }
        )
        passed = False
    stopped = any(item.get("status") == "stopped" for item in step_results)
    for item in step_results:
        if item.get("assertion"):
            assertions.append(item["assertion"])
    error_message = "" if passed else ("用户手动停止任务" if stopped else _first_error(step_results))
    response_snapshot = {"steps": step_results, "screenshots": screenshots}
    error_analysis = "" if passed or stopped else analyze_ui_error(db, case, error_message, step_results)
    if error_analysis:
        response_snapshot["error_analysis"] = error_analysis
    row = _save_result(
        db,
        task.id,
        case.id,
        "passed" if passed else ("stopped" if stopped else "failed"),
        _ui_request_snapshot(case, env, current_url or case.start_url, steps),
        response_snapshot,
        assertions,
        duration_ms,
        error_message,
    )
    _save_artifacts(db, task.id, row.id, screenshots)
    return row


def ui_task_stop_requested(db: Session, task: ExecutionTask) -> bool:
    db.refresh(task)
    summary = parse_json(task.summary_json, {})
    return task.status == "stopped" or bool(summary.get("stop_requested"))


def _ui_request_snapshot(case: UiTestCase, env: Environment, start_url: str, steps: list[dict]) -> dict:
    return {
        "mode": "advanced",
        "browser": _ui_browser_channel(case),
        "headless": _ui_headless(case),
        "user_agent": DEFAULT_UI_USER_AGENT,
        "locale": DEFAULT_UI_LOCALE,
        "wait_until": _ui_wait_until(case),
        "wait_after_load_ms": _ui_wait_after_load_ms(case),
        "start_url": start_url,
        "max_steps": len(steps),
        "step_timeout_ms": case.step_timeout_ms,
        "environment": {"id": env.id, "name": env.name},
        "steps": steps,
    }


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
        return page.get_by_text(target).first, None
    if locator_type == "xpath":
        return page.locator(f"xpath={target}"), None
    if locator_type == "placeholder":
        return page.get_by_placeholder(target), None
    if locator_type == "role":
        return page.get_by_role("button", name=target).first, None
    return page.locator(target), None


def _run_step(db: Session, page, step: dict, index: int, task_id: int, case: UiTestCase) -> dict:
    action = str(step.get("action") or "")
    value = render_ui_dynamic_value(str(step.get("value") or ""))
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
            _wait_for_page_ready(page, case.step_timeout_ms)
            locator.click()
            _settle_page(page, case.step_timeout_ms)
            _wait_for_page_ready(page, case.step_timeout_ms, "after_action")
            page.wait_for_timeout(1500)
        elif action == "dblclick":
            locator, ai_locator = _locator(page, step, db)
            if ai_locator:
                result["ai_locator"] = ai_locator
            _wait_for_page_ready(page, case.step_timeout_ms)
            locator.dblclick()
            _settle_page(page, case.step_timeout_ms)
            _wait_for_page_ready(page, case.step_timeout_ms, "after_action")
            page.wait_for_timeout(1500)
        elif action == "fill":
            locator, ai_locator = _locator(page, step, db)
            if ai_locator:
                result["ai_locator"] = ai_locator
            _wait_for_page_ready(page, case.step_timeout_ms)
            locator.fill(value)
            locator.dispatch_event("input")
            locator.dispatch_event("change")
            locator.dispatch_event("blur")
            page.wait_for_timeout(300)
        elif action == "select":
            locator, ai_locator = _locator(page, step, db)
            if ai_locator:
                result["ai_locator"] = ai_locator
            _wait_for_page_ready(page, case.step_timeout_ms)
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
                _settle_page(page, min(case.step_timeout_ms, 5000))
                _wait_for_page_ready(page, min(case.step_timeout_ms, 5000), "after_action")
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
                    if 0 < timeout_ms < 1000:
                        timeout_ms *= 1000
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
        raw_error = str(exc)
        result["status"] = "error"
        result["message"] = explain_ui_error(raw_error, step)
        result["raw_error"] = raw_error
    return result


def render_ui_dynamic_value(value: str) -> str:
    if not isinstance(value, str) or "${random." not in value:
        return value

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        args = _parse_dynamic_args(match.group(2))
        try:
            if name == "string":
                length = _arg_int(args, 0, 8, 1, 128)
                alphabet = string.ascii_uppercase + string.digits
                return "".join(random.choice(alphabet) for _ in range(length))
            if name == "number":
                if len(args) >= 2:
                    minimum = int(args[0])
                    maximum = int(args[1])
                else:
                    digits = _arg_int(args, 0, 6, 1, 18)
                    minimum = 0 if digits == 1 else 10 ** (digits - 1)
                    maximum = (10 ** digits) - 1
                if minimum > maximum:
                    minimum, maximum = maximum, minimum
                return str(random.randint(minimum, maximum))
            if name == "uuid":
                return str(uuid.uuid4())
            if name == "vin":
                return "".join(random.choice(VIN_CHARS) for _ in range(17))
            if name == "phone":
                prefixes = ("130", "131", "132", "155", "156", "166", "176", "185", "186", "188")
                return random.choice(prefixes) + "".join(random.choice(string.digits) for _ in range(8))
            if name == "date":
                fmt = args[0] if args else "yyyyMMddHHmmss"
                return datetime.now().strftime(_date_format_to_strftime(fmt))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"动态值表达式参数错误: {match.group(0)}") from exc
        raise RuntimeError(f"不支持的动态值表达式: {match.group(0)}")

    return UI_DYNAMIC_PATTERN.sub(replace, value)


def _parse_dynamic_args(raw: str) -> list[str]:
    return [item.strip().strip("\"'") for item in (raw or "").split(",") if item.strip()]


def _arg_int(args: list[str], index: int, default: int, minimum: int, maximum: int) -> int:
    value = int(args[index]) if len(args) > index else default
    return min(max(value, minimum), maximum)


def _date_format_to_strftime(fmt: str) -> str:
    return (
        fmt.replace("yyyy", "%Y")
        .replace("MM", "%m")
        .replace("dd", "%d")
        .replace("HH", "%H")
        .replace("mm", "%M")
        .replace("ss", "%S")
    )


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
    setting = get_active_ai_setting(db)
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


def analyze_ui_error(db: Session, case: UiTestCase | None, error_message: str, steps: list[dict]) -> str:
    setting = get_active_ai_setting(db)
    if not setting or not setting.provider_url or not setting.model_name or not error_message:
        return ""
    last_steps = [
        {
            "index": item.get("index"),
            "action": item.get("action"),
            "target": item.get("target"),
            "status": item.get("status"),
            "message": item.get("message"),
        }
        for item in steps[-5:]
        if isinstance(item, dict)
    ]
    payload = {
        "model": setting.model_name,
        "messages": [
            {
                "role": "system",
                "content": "你是UI自动化失败分析助手。用中文输出一句到两句话，简单明了说明失败原因和建议，不要Markdown。",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "case_name": case.name if case else "",
                        "test_goal": case.test_goal if case else "",
                        "error_message": error_message,
                        "recent_steps": last_steps,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0,
        "max_tokens": 120,
    }
    headers = {"Content-Type": "application/json"}
    if setting.api_key:
        headers["Authorization"] = f"Bearer {setting.api_key}"
    try:
        response = httpx.post(_chat_completions_url(setting.provider_url), json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return str(content or "").strip()[:500]
    except Exception:
        return ""


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


def explain_ui_error(error_message: str, step: dict | None = None) -> str:
    raw = str(error_message or "")
    lower = raw.lower()
    action = str((step or {}).get("action") or "")
    target = str((step or {}).get("target") or "")
    locator_type = str((step or {}).get("locator_type") or "")
    prefix = f"当前步骤{_ui_step_action_label(action)}失败"
    if target:
        prefix += f"，定位：{target}"
    if "strict mode violation" in lower and "resolved to" in lower:
        return (
            f"{prefix}。定位命中了多个元素，平台无法判断该操作哪一个。"
            "请把定位写得更精确，例如使用 input[name=\"字段名\"]、button[id=\"按钮ID\"]，或补充元素层级。"
        )
    if "intercepts pointer events" in lower or "element intercepts pointer events" in lower:
        return (
            f"{prefix}。目标元素被遮罩、弹窗或加载层挡住，点击没有真正落到元素上。"
            "请在该步骤前增加等待，或等待页面加载遮罩消失后再操作。"
        )
    if "页面加载遮罩一直未消失" in raw:
        return raw
    if "timeout" in lower and ("locator" in lower or "waiting for" in lower):
        if "fill" in lower:
            verb = "输入"
        elif "click" in lower:
            verb = "点击"
        elif "select" in lower:
            verb = "选择"
        else:
            verb = "操作"
        return (
            f"{prefix}。等待元素可{verb}超时，可能是页面未加载完、弹窗未出现、定位写错或元素被禁用。"
            "建议先加等待步骤，再用元素拾取重新确认定位。"
        )
    if "not visible" in lower or "element is not visible" in lower:
        return f"{prefix}。元素存在但当前不可见，请确认是否需要先展开区域、滚动页面或等待弹窗显示。"
    if "not enabled" in lower or "disabled" in lower:
        return f"{prefix}。元素当前不可操作或被禁用，请确认前置字段是否填写完整、页面状态是否允许操作。"
    if "选择下拉项失败" in raw:
        return raw
    return raw or f"{prefix}。步骤执行失败，请查看截图确认页面状态。"


def _ui_step_action_label(action: str) -> str:
    mapping = {
        "goto": "打开页面",
        "click": "点击",
        "dblclick": "双击",
        "fill": "输入",
        "select": "选择",
        "wait": "等待",
        "assert_text": "断言文本",
        "assert_visible": "断言元素",
        "screenshot": "截图",
    }
    return mapping.get(action, action or "操作")


def _needs_explicit_advanced_result(case: UiTestCase, steps: list[dict]) -> bool:
    if not str(getattr(case, "assertion_goal", "") or "").strip():
        return False
    if any(item.get("assertion") for item in steps):
        return False
    last_action = str((steps[-1] if steps else {}).get("action") or "")
    return last_action == "screenshot"


def _settle_page(page, timeout_ms: int) -> None:
    wait_ms = min(max(int(timeout_ms or 5000), 1000), 10000)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=wait_ms)
    except Exception:
        pass
    try:
        page.wait_for_load_state("networkidle", timeout=wait_ms)
    except Exception:
        pass


def _wait_for_page_ready(page, timeout_ms: int = 10000, phase: str = "before_action") -> None:
    wait_ms = min(max(int(timeout_ms or 10000), 1000), 30000)
    blocking_selectors = [
        ".loader-indicator",
        ".loading",
        ".loading-mask",
        ".nfs-loading",
        ".ant-spin-spinning",
        ".ant-spin-nested-loading > .ant-spin",
        "[class*='loading'][style*='display: block']",
        "[class*='spinner']",
    ]
    for selector in blocking_selectors:
        try:
            page.locator(selector).first.wait_for(state="hidden", timeout=wait_ms)
        except Exception as exc:
            if selector == ".loader-indicator":
                if phase == "after_action":
                    raise RuntimeError("动作已经触发，但页面加载遮罩长时间未消失，可能是业务接口响应慢、后端异常，或提交/查询后的弹窗没有返回。") from exc
                raise RuntimeError("页面加载遮罩一直未消失，目标元素暂时不能操作，请检查查询或弹窗加载是否卡住。") from exc
    try:
        page.wait_for_function(
            """() => !document.querySelector('.loader-indicator, .loading-mask, .ant-spin-spinning')""",
            timeout=min(wait_ms, 5000),
        )
    except Exception:
        pass


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
