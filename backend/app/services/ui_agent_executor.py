import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..models import AiSetting, Environment, ExecutionResult, ExecutionTask, UiTestCase
from ..utils import dump_json, parse_json
from .ai_settings import get_active_ai_setting
from .ui_executor import (
    ARTIFACT_ROOT,
    DEFAULT_UI_LOCALE,
    DEFAULT_UI_USER_AGENT,
    UiResultView,
    analyze_ui_error,
    _goto_and_wait,
    _ui_headless,
    _launch_ui_browser,
    _save_artifacts,
    _save_result,
    _wait_for_page_ready,
    build_ui_url,
    explain_ui_error,
    ui_task_stop_requested,
)


ALLOWED_AGENT_ACTIONS = {"click", "dblclick", "fill", "select", "wait", "assert_text", "screenshot", "finish"}
SENSITIVE_KEYS = ("password", "passwd", "secret", "token", "key", "密码", "密钥", "令牌")
ARTIFACT_RETENTION_DAYS = 7
ACTION_ALIASES = {
    "点击": "click",
    "单击": "click",
    "click_element": "click",
    "double_click": "dblclick",
    "双击": "dblclick",
    "输入": "fill",
    "填写": "fill",
    "type": "fill",
    "input": "fill",
    "选择": "select",
    "下拉选择": "select",
    "等待": "wait",
    "断言文本": "assert_text",
    "检查文本": "assert_text",
    "截图": "screenshot",
    "完成": "finish",
    "结束": "finish",
    "成功": "finish",
    "失败": "finish",
}


class AgentModelError(RuntimeError):
    def __init__(self, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}


def execute_ui_agent_case(db: Session, task: ExecutionTask) -> ExecutionResult:
    case = db.get(UiTestCase, task.target_id)
    env = db.get(Environment, task.environment_id)
    started = time.perf_counter()
    if not case or case.is_deleted or not env:
        return _save_result(db, task.id, task.target_id, "error", {}, {"agent_steps": []}, [], 0, "UI用例或环境不存在")

    setting = get_active_ai_setting(db)
    if not setting or setting.status != "active" or not setting.provider_url or not setting.model_name:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return _save_result(
            db,
            task.id,
            case.id,
            "error",
            _agent_request_snapshot(case, env, ""),
            {"agent_steps": []},
            [],
            duration_ms,
            "AI配置未启用，AI模式无法执行。请先在 UI测试 -> AI配置 中配置模型服务。",
        )

    _cleanup_old_artifacts()
    agent_steps: list[dict[str, Any]] = []
    screenshots: list[dict[str, Any]] = []
    assertions: list[dict[str, Any]] = []
    current_url = ""
    final_status = "failed"
    error_message = ""
    _update_task_progress(db, task, agent_steps, screenshots, "running", "AI执行已启动，正在准备浏览器")
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return _save_result(
            db,
            task.id,
            case.id,
            "error",
            _agent_request_snapshot(case, env, ""),
            {"agent_steps": []},
            [],
            duration_ms,
            f"Playwright未安装或浏览器依赖缺失: {exc}",
        )

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
                current_url = build_ui_url(env, case.start_url or "/")
                _goto_and_wait(page, current_url, case)
                initial_screenshot = save_agent_screenshot(page, task.id, 0, "initial")
                if initial_screenshot:
                    screenshots.append(initial_screenshot)
                _update_task_progress(db, task, agent_steps, screenshots, "running", "页面已打开，正在进行AI观察")
                for index in range(1, _max_steps(case) + 1):
                    if ui_task_stop_requested(db, task):
                        final_status = "stopped"
                        error_message = "用户手动停止任务"
                        agent_steps.append({"index": index, "action": "stop", "status": "stopped", "message": error_message})
                        _update_task_progress(db, task, agent_steps, screenshots, "stopped", error_message)
                        break
                    observation = observe_page(page)
                    decision = decide_next_action(setting, case, observation, agent_steps)
                    if ui_task_stop_requested(db, task):
                        final_status = "stopped"
                        error_message = "用户手动停止任务"
                        agent_steps.append({"index": index, "action": "stop", "status": "stopped", "message": error_message})
                        _update_task_progress(db, task, agent_steps, screenshots, "stopped", error_message)
                        break
                    result = run_agent_action(page, decision, observation, index, case)
                    result["url"] = page.url
                    result["page_title"] = _safe_page_title(page)
                    repeated_message = _repeated_action_message(agent_steps, result)
                    if repeated_message:
                        result["status"] = "failed"
                        result["message"] = repeated_message
                    agent_steps.append(result)
                    screenshot = save_agent_screenshot(page, task.id, index, result["status"])
                    if screenshot:
                        result["screenshot"] = screenshot
                        screenshots.append(screenshot)
                    if result.get("assertion"):
                        assertions.append(result["assertion"])
                    _update_task_progress(db, task, agent_steps, screenshots, "running")
                    if result["action"] == "finish":
                        final_status = "passed" if result.get("success") else "failed"
                        error_message = "" if final_status == "passed" else str(result.get("message") or "AI判定执行失败")
                        break
                    if result["status"] != "passed":
                        final_status = "failed"
                        error_message = str(result.get("message") or "UI Agent步骤执行失败")
                        break
                else:
                    final_status = "failed"
                    error_message = f"已达到最大步骤数 {_max_steps(case)}，AI未给出完成结论"
            finally:
                browser.close()
    except AgentModelError as exc:
        final_status = "error"
        error_message = str(exc)
        agent_steps.append({
            "index": len(agent_steps) + 1,
            "action": "model_call",
            "status": "error",
            "message": str(exc),
            "model_error": exc.detail,
        })
        _update_task_progress(db, task, agent_steps, screenshots, "error", error_message)
    except (PlaywrightError, PlaywrightTimeoutError, Exception) as exc:
        final_status = "error"
        raw_error = str(exc)
        error_message = explain_ui_error(raw_error)
        agent_steps.append({"index": len(agent_steps) + 1, "action": "error", "status": "error", "message": error_message, "raw_error": raw_error})
        _update_task_progress(db, task, agent_steps, screenshots, "error", error_message)

    duration_ms = int((time.perf_counter() - started) * 1000)
    response_snapshot = {"agent_steps": agent_steps, "screenshots": screenshots, "token_usage": _sum_token_usage(agent_steps)}
    error_analysis = "" if final_status in {"passed", "stopped"} else analyze_ui_error(db, case, error_message, agent_steps)
    if error_analysis:
        response_snapshot["error_analysis"] = error_analysis
    row = _save_result(
        db,
        task.id,
        case.id,
        final_status,
        _agent_request_snapshot(case, env, current_url),
        response_snapshot,
        assertions,
        duration_ms,
        error_message,
    )
    _save_artifacts(db, task.id, row.id, screenshots)
    return row


def _update_task_progress(
    db: Session,
    task: ExecutionTask,
    agent_steps: list[dict[str, Any]],
    screenshots: list[dict[str, Any]],
    status: str,
    message: str = "",
) -> None:
    task.summary_json = dump_json({
        "ui_progress": True,
        "status": status,
        "message": message,
        "agent_steps": agent_steps,
        "screenshots": screenshots,
        "token_usage": _sum_token_usage(agent_steps),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    db.commit()


def observe_page(page) -> dict[str, Any]:
    script = """
    () => {
      const clean = value => String(value || '').replace(/\\s+/g, ' ').trim();
      const quote = value => {
        const text = String(value || '');
        if (!text.includes("'")) return "'" + text + "'";
        if (!text.includes('"')) return '"' + text + '"';
        return "concat('" + text.replace(/'/g, "',\\"'\\",'") + "')";
      };
      const segment = el => {
        const tag = el.tagName.toLowerCase();
        if (!el.parentElement) return tag;
        const siblings = Array.from(el.parentElement.children).filter(item => item.tagName === el.tagName);
        if (siblings.length === 1) return tag;
        return `${tag}[${siblings.indexOf(el) + 1}]`;
      };
      const xpath = el => {
        const id = el.id || '';
        if (id) {
          const count = document.evaluate(`count(//*[@id=${quote(id)}])`, document, null, XPathResult.NUMBER_TYPE, null).numberValue;
          if (count === 1) return `//*[@id=${quote(id)}]`;
        }
        const name = el.getAttribute('name') || '';
        if (name) {
          const count = document.evaluate(`count(//*[@name=${quote(name)}])`, document, null, XPathResult.NUMBER_TYPE, null).numberValue;
          if (count === 1) return `//*[@name=${quote(name)}]`;
        }
        const parts = [];
        let node = el;
        while (node && node.nodeType === 1) {
          parts.unshift(segment(node));
          node = node.parentElement;
        }
        return '/' + parts.join('/');
      };
      const selector = 'button,a,input,textarea,select,[role],[aria-label],[placeholder],label,[data-testid],[id],[name]';
      const elements = Array.from(document.querySelectorAll(selector));
      const candidates = [];
      for (const el of elements) {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        const visible = rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
        if (!visible) continue;
        const tag = String(el.tagName || '').toLowerCase();
        const type = clean(el.getAttribute('type'));
        const disabled = !!el.disabled || el.getAttribute('aria-disabled') === 'true';
        if (disabled && ['button', 'input', 'textarea', 'select'].includes(tag)) continue;
        const options = tag === 'select'
          ? Array.from(el.options || []).map(option => ({ value: option.value || '', label: clean(option.label || option.textContent || option.value), selected: !!option.selected }))
          : [];
        candidates.push({
          ref: `e${candidates.length + 1}`,
          tag,
          role: clean(el.getAttribute('role')),
          text: clean(el.innerText || el.textContent || (type === 'password' ? '' : el.value)).slice(0, 120),
          placeholder: clean(el.getAttribute('placeholder')),
          aria: clean(el.getAttribute('aria-label')),
          id: clean(el.id),
          name: clean(el.getAttribute('name')),
          type,
          xpath: xpath(el),
          options
        });
        if (candidates.length >= 120) break;
      }
      return {
        url: location.href,
        title: document.title,
        visible_text: clean(document.body ? document.body.innerText : '').slice(0, 4000),
        candidates
      };
    }
    """
    try:
        value = page.evaluate(script)
        return value if isinstance(value, dict) else {"candidates": [], "visible_text": ""}
    except Exception as exc:
        return {"candidates": [], "visible_text": "", "error": str(exc)}


def decide_next_action(setting: AiSetting, case: UiTestCase, observation: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    system = (
        "你是一个受控的Web UI自动化执行Agent。只能返回JSON对象，不要返回Markdown。"
        "禁止输出解释、代码块、前缀、后缀、列表或自然语言；整个回复必须是一个JSON对象。"
        "可用动作：click、dblclick、fill、select、wait、assert_text、screenshot、finish。"
        "必须只使用current_page.candidates中当前可见可操作元素的ref字段，不要复用history里的旧ref或旧XPath。"
        "如果刚点击搜索/查询后页面还没出现目标结果，优先wait 2000到5000毫秒，不要反复点击同一个搜索按钮或结果区域。"
        "同一个动作同一个元素连续执行2次后仍无进展，应finish且success=false说明卡住原因。"
        "不要对disabled/不可编辑控件执行fill/select/click；不要请求打开外部网址；不确定时使用wait或finish失败。"
        "需要输入或选择test_data中的数据时，value必须返回变量引用，例如${用户名}、${密码}，禁止自行编造账号、密码或随机长串。"
        "如果测试数据中密码是1，仍然返回${密码}，不要返回******，也不要生成其它密码。"
        "返回格式：{\"action\":\"click|dblclick|fill|select|wait|assert_text|screenshot|finish\","
        "\"ref\":\"e1\",\"value\":\"\",\"reason\":\"\",\"success\":true,\"message\":\"\"}。"
        "示例：{\"action\":\"click\",\"ref\":\"e3\",\"value\":\"\",\"reason\":\"点击登录按钮\",\"success\":false,\"message\":\"\"}。"
        "finish表示用例结束，success=true为通过，success=false为失败。"
    )
    user = {
        "test_goal": case.test_goal,
        "assertion_goal": case.assertion_goal,
        "test_data": _mask_sensitive(parse_json(case.test_data_json, {})),
        "allow_ai_actions": bool(case.allow_ai_actions),
        "current_page": observation,
        "history": _compact_history(history),
    }
    payload = {
        "model": setting.model_name,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json"}
    if setting.api_key:
        headers["Authorization"] = f"Bearer {setting.api_key}"
    url = _chat_completions_url(setting.provider_url)
    response = _post_chat_completion(url, payload, headers)
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    decision = normalize_agent_decision(content)
    decision["token_usage"] = _token_usage(data)
    return decision


def _post_chat_completion(url: str, payload: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
    try:
        response = _post_chat_completion_once(url, payload, headers)
        if response.status_code == 400 and payload.get("response_format"):
            retry_payload = {key: value for key, value in payload.items() if key != "response_format"}
            retry_response = _post_chat_completion_once(url, retry_payload, headers)
            if retry_response.status_code < 400:
                return retry_response
            response = retry_response
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as exc:
        response = exc.response
        raise AgentModelError(
            f"AI模型请求失败：HTTP {response.status_code}",
            {
                "request_url": url,
                "model": payload.get("model", ""),
                "status_code": response.status_code,
                "retry_count": int(response.extensions.get("retry_count", 0)),
                "response": _response_preview(response),
                "hint": _model_error_hint(url, response),
            },
        ) from exc
    except httpx.RequestError as exc:
        raise AgentModelError(
            "AI模型请求连接失败",
            {
                "request_url": url,
                "model": payload.get("model", ""),
                "error": str(exc),
                "retry_count": int(getattr(exc, "retry_count", 0) or 0),
                "hint": _request_error_hint(url, exc),
            },
        ) from exc


def _post_chat_completion_once(url: str, payload: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
    last_error: httpx.RequestError | None = None
    retry_statuses = {429, 500, 502, 503, 504}
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=httpx.Timeout(60.0, connect=15.0))
            response.extensions["retry_count"] = attempt
            if response.status_code in retry_statuses and attempt < max_attempts - 1:
                time.sleep(_retry_delay(attempt))
                continue
            return response
        except httpx.RequestError as exc:
            last_error = exc
            setattr(last_error, "retry_count", attempt)
            if attempt < max_attempts - 1:
                time.sleep(_retry_delay(attempt))
                continue
            setattr(last_error, "retry_count", attempt)
            raise
    if last_error:
        raise last_error
    raise RuntimeError("AI模型请求未返回响应")


def _retry_delay(attempt: int) -> float:
    return (1.0, 3.0, 8.0)[min(max(attempt, 0), 2)]


def normalize_agent_decision(content: str | dict[str, Any]) -> dict[str, Any]:
    data: Any = _extract_agent_decision_json(content)
    if not isinstance(data, dict):
        raise RuntimeError("AI动作必须是JSON对象")
    action = _normalize_agent_action(data.get("action") or data.get("操作") or data.get("type") or data.get("name"))
    if action not in ALLOWED_AGENT_ACTIONS:
        raise RuntimeError(f"AI返回了不支持的动作：{action or '-'}")
    return {
        "action": action,
        "ref": str(data.get("ref") or data.get("element_ref") or data.get("元素") or "").strip(),
        "target": str(data.get("target") or data.get("selector") or data.get("xpath") or data.get("目标") or "").strip(),
        "locator_type": str(data.get("locator_type") or data.get("locatorType") or data.get("定位方式") or "xpath").strip(),
        "value": str(data.get("value") or data.get("text") or data.get("input") or data.get("值") or ""),
        "reason": str(data.get("reason") or data.get("理由") or data.get("说明") or ""),
        "success": _as_bool(data.get("success")) if action == "finish" else False,
        "message": str(data.get("message") or data.get("消息") or ""),
    }


def _extract_agent_decision_json(content: str | dict[str, Any]) -> Any:
    if not isinstance(content, str):
        return content
    text = content.strip()
    if not text:
        raise RuntimeError("AI未返回可识别的JSON动作")
    for candidate in _agent_json_candidates(text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"AI未返回可识别的JSON动作，原始返回：{text[:300]}")


def _agent_json_candidates(text: str) -> list[str]:
    candidates = [text]
    candidates.extend(match.group(1).strip() for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I))
    candidates.extend(_balanced_json_objects(text))
    return [item for item in dict.fromkeys(candidates) if item]


def _balanced_json_objects(text: str) -> list[str]:
    objects: list[str] = []
    start = -1
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth:
            depth -= 1
            if depth == 0 and start >= 0:
                objects.append(text[start : index + 1])
                start = -1
    return objects


def _normalize_agent_action(value: Any) -> str:
    action = str(value or "").strip()
    return ACTION_ALIASES.get(action, action)


def run_agent_action(page, decision: dict[str, Any], observation: dict[str, Any], index: int, case: UiTestCase) -> dict[str, Any]:
    action = decision["action"]
    started = time.perf_counter()
    raw_value = str(decision.get("value") or "")
    resolved_value, value_key = _resolve_agent_value(raw_value, decision, observation, case)
    result = {
        "index": index,
        "action": action,
        "ref": decision.get("ref", ""),
        "target": decision.get("target", ""),
        "value": _mask_value(value_key or "value", resolved_value),
        "reason": decision.get("reason", ""),
        "token_usage": decision.get("token_usage") or {},
        "status": "passed",
        "message": decision.get("message") or "通过",
    }
    try:
        if not case.allow_ai_actions and action in {"click", "dblclick", "fill", "select"}:
            raise RuntimeError("当前用例未允许AI自主点击/输入")
        if action == "finish":
            result["success"] = bool(decision.get("success"))
            result["status"] = "passed" if result["success"] else "failed"
            result["message"] = decision.get("message") or ("AI判定用例通过" if result["success"] else "AI判定用例失败")
            return _finish_agent_result(result, started)
        if action == "wait":
            timeout = _safe_timeout(resolved_value, case.step_timeout_ms)
            page.wait_for_timeout(timeout)
            result["value"] = str(timeout)
            result["message"] = f"已等待 {timeout}ms"
            return _finish_agent_result(result, started)
        if action == "screenshot":
            result["message"] = "已截图"
            return _finish_agent_result(result, started)
        if action == "assert_text":
            expected = resolved_value or decision.get("target") or ""
            visible = page.get_by_text(str(expected)).first.is_visible(timeout=case.step_timeout_ms)
            result["assertion"] = {"type": "ui_agent_assert_text", "path": str(expected), "expected": "可见", "actual": "可见" if visible else "不可见", "passed": visible, "message": "通过" if visible else "未找到文本"}
            if not visible:
                result["status"] = "failed"
                result["message"] = f"未找到文本：{expected}"
            return _finish_agent_result(result, started)
        resolved_target = _target_from_ref(decision, observation)
        result["locator_type"] = resolved_target.get("locator_type", "xpath")
        result["target"] = resolved_target.get("target", result.get("target", ""))
        locator = _locator_for_target(page, resolved_target)
        if action == "click":
            _wait_for_page_ready(page, case.step_timeout_ms)
            locator.click(timeout=case.step_timeout_ms)
            _settle_page(page, case.step_timeout_ms)
            _wait_for_page_ready(page, case.step_timeout_ms, "after_action")
            page.wait_for_timeout(1500)
        elif action == "dblclick":
            _wait_for_page_ready(page, case.step_timeout_ms)
            locator.dblclick(timeout=case.step_timeout_ms)
            _settle_page(page, case.step_timeout_ms)
            _wait_for_page_ready(page, case.step_timeout_ms, "after_action")
            page.wait_for_timeout(1500)
        elif action == "fill":
            _wait_for_page_ready(page, case.step_timeout_ms)
            locator.fill(resolved_value, timeout=case.step_timeout_ms)
            locator.dispatch_event("input")
            locator.dispatch_event("change")
            locator.dispatch_event("blur")
            page.wait_for_timeout(300)
        elif action == "select":
            value = resolved_value
            _wait_for_page_ready(page, case.step_timeout_ms)
            try:
                locator.select_option(value, timeout=case.step_timeout_ms)
            except Exception:
                locator.select_option(label=value, timeout=case.step_timeout_ms)
            locator.dispatch_event("input")
            locator.dispatch_event("change")
            locator.dispatch_event("blur")
            _settle_page(page, min(case.step_timeout_ms, 5000))
            _wait_for_page_ready(page, min(case.step_timeout_ms, 5000), "after_action")
            page.wait_for_timeout(800)
        page.wait_for_timeout(500)
    except Exception as exc:
        raw_error = str(exc)
        result["status"] = "error"
        result["message"] = explain_ui_error(raw_error, {"action": action, "locator_type": result.get("locator_type"), "target": result.get("target")})
        result["raw_error"] = raw_error
    return _finish_agent_result(result, started)


def _finish_agent_result(result: dict[str, Any], started: float) -> dict[str, Any]:
    result["duration_ms"] = int((time.perf_counter() - started) * 1000)
    return result


def _resolve_agent_value(raw_value: str, decision: dict[str, Any], observation: dict[str, Any], case: UiTestCase) -> tuple[str, str]:
    test_data = parse_json(case.test_data_json, {})
    if not isinstance(test_data, dict):
        return raw_value, ""
    resolved, key = _replace_test_data_variables(raw_value, test_data)
    if key:
        return resolved, key
    if decision.get("action") == "fill":
        inferred_key = _infer_fill_data_key(decision, observation, test_data)
        if inferred_key and _should_override_agent_value(raw_value, inferred_key):
            return str(test_data.get(inferred_key) or ""), inferred_key
    return raw_value, ""


def _replace_test_data_variables(value: str, test_data: dict[str, Any]) -> tuple[str, str]:
    text = str(value or "")
    matched_keys: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key in test_data:
            matched_keys.append(key)
            return str(test_data.get(key) or "")
        return match.group(0)

    resolved = re.sub(r"\$\{([^{}]+)\}", replace, text)
    return resolved, matched_keys[0] if len(matched_keys) == 1 else ""


def _infer_fill_data_key(decision: dict[str, Any], observation: dict[str, Any], test_data: dict[str, Any]) -> str:
    ref = str(decision.get("ref") or "")
    target_text = " ".join(
        str(value or "")
        for value in (
            decision.get("target"),
            decision.get("reason"),
            decision.get("message"),
            _candidate_text_by_ref(observation, ref),
        )
    ).lower()
    password_keys = [key for key in test_data if _is_sensitive_key(key)]
    if password_keys and ("password" in target_text or "passwd" in target_text or "密码" in target_text):
        return password_keys[0]
    for key in test_data:
        if str(key).lower() in target_text:
            return key
    return ""


def _candidate_text_by_ref(observation: dict[str, Any], ref: str) -> str:
    for item in observation.get("candidates") or []:
        if not isinstance(item, dict) or str(item.get("ref") or "") != ref:
            continue
        return " ".join(str(item.get(key) or "") for key in ("text", "placeholder", "aria", "id", "name", "type"))
    return ""


def _agent_locator(page, decision: dict[str, Any], observation: dict[str, Any]):
    target = _target_from_ref(decision, observation)
    return _locator_for_target(page, target)


def _locator_for_target(page, target: dict[str, str]):
    locator_type = str(target.get("locator_type") or "xpath")
    value = str(target.get("target") or "")
    if locator_type == "css":
        return page.locator(value).first
    if locator_type == "text":
        return page.get_by_text(value).first
    if locator_type == "placeholder":
        return page.get_by_placeholder(value).first
    if locator_type == "role":
        return page.get_by_role("button", name=value).first
    return page.locator(f"xpath={value}").first


def _target_from_ref(decision: dict[str, Any], observation: dict[str, Any]) -> dict[str, str]:
    ref = str(decision.get("ref") or "")
    for item in observation.get("candidates") or []:
        if str(item.get("ref") or "") == ref:
            return {"locator_type": "xpath", "target": str(item.get("xpath") or "")}
    if ref:
        raise RuntimeError(f"AI返回的元素引用 {ref} 不在当前页面可操作元素中，请重新观察页面后再操作")
    return {"locator_type": str(decision.get("locator_type") or "xpath"), "target": str(decision.get("target") or "")}


def save_agent_screenshot(page, task_id: int, step_index: int, status: str) -> dict[str, Any] | None:
    try:
        ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        suffix = "failure" if status != "passed" else "agent"
        path = ARTIFACT_ROOT / f"task-{task_id}-agent-step-{step_index}-{suffix}.png"
        page.screenshot(path=str(path), full_page=True)
        return {"step_index": step_index, "type": f"{suffix}_screenshot", "path": str(path).replace("\\", "/")}
    except Exception:
        return None


def _agent_request_snapshot(case: UiTestCase, env: Environment, current_url: str) -> dict[str, Any]:
    return {
        "mode": "ai",
        "browser": getattr(case, "browser_channel", None) or "chromium",
        "headless": _ui_headless(case),
        "user_agent": DEFAULT_UI_USER_AGENT,
        "locale": DEFAULT_UI_LOCALE,
        "start_url": current_url or case.start_url,
        "test_goal": case.test_goal,
        "test_data": _mask_sensitive(parse_json(case.test_data_json, {})),
        "assertion_goal": case.assertion_goal,
        "max_steps": _max_steps(case),
        "step_timeout_ms": case.step_timeout_ms,
        "environment": {"id": env.id, "name": env.name},
    }


def _chat_completions_url(provider_url: str) -> str:
    value = (provider_url or "").strip().rstrip("/")
    if value.endswith("/chat/completions"):
        return value
    if value in {"https://api.deepseek.com", "http://api.deepseek.com"}:
        value = f"{value}/v1"
    return f"{value}/chat/completions"


def _response_preview(response: httpx.Response) -> Any:
    text = response.text[:2000]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _model_error_hint(url: str, response: httpx.Response) -> str:
    text = response.text.lower()
    if "api.deepseek.com/chat/completions" in url and "/v1/" not in url:
        return "DeepSeek 地址应配置为 https://api.deepseek.com/v1，平台也会自动为 api.deepseek.com 补 /v1。"
    if "model" in text and ("not" in text or "invalid" in text or "不存在" in text):
        return "请检查模型名称是否可用，例如你当前想使用 deepseek-v4-flash。"
    if "response_format" in text:
        return "模型可能不支持 response_format，平台已自动去掉 response_format 重试；若仍失败请看响应内容。"
    if response.status_code in {401, 403}:
        return "请检查 API Key 是否正确、是否有模型调用权限。"
    return "请查看 response 字段中的模型服务原始错误。"


def _request_error_hint(url: str, exc: httpx.RequestError) -> str:
    text = str(exc).lower()
    if "unexpected_eof_while_reading" in text or "eof occurred in violation of protocol" in text or "wrong version number" in text:
        if url.startswith("https://"):
            return "SSL握手失败。请优先确认模型服务地址是否实际只支持 http://；如果必须使用 https，请检查模型网关证书、反向代理 TLS 配置和公司代理是否中断了连接。"
        return "SSL/TLS连接异常。请检查模型网关证书、反向代理 TLS 配置和公司代理。"
    if "certificate" in text or "cert" in text:
        return "模型服务证书校验失败。请检查证书是否过期、域名是否匹配，或改用受信任的模型网关地址。"
    if "name or service not known" in text or "getaddrinfo" in text or "nodename nor servname" in text:
        return "模型服务域名解析失败。请检查服务地址、DNS、代理或容器网络配置。"
    if "connection refused" in text or "connecterror" in text:
        return "模型服务拒绝连接。请确认服务已启动、端口正确，并且容器能访问该地址。"
    if "timed out" in text or "timeout" in text:
        return "模型服务请求超时。请检查网络连通性、模型服务负载，或稍后重试。"
    return "请检查模型服务地址、网络连通性、代理和服务器 DNS。"


def _compact_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "index": item.get("index"),
            "action": item.get("action"),
            "ref": item.get("ref"),
            "target": item.get("target"),
            "status": item.get("status"),
            "message": item.get("message"),
        }
        for item in history[-10:]
    ]


def _action_identity(item: dict[str, Any]) -> tuple[str, str, str]:
    action = str(item.get("action") or "")
    target = str(item.get("target") or item.get("ref") or "")
    value = str(item.get("value") or "")
    return action, target, value


def _repeated_action_message(history: list[dict[str, Any]], current: dict[str, Any]) -> str:
    action = str(current.get("action") or "")
    if action not in {"click", "select"} or current.get("status") != "passed":
        return ""
    current_identity = _action_identity(current)
    same_count = 1
    for item in reversed(history):
        if item.get("status") != "passed" or _action_identity(item) != current_identity:
            break
        same_count += 1
    if same_count >= 3:
        return "检测到连续重复执行同一操作，疑似页面未加载出目标元素或AI判断陷入循环，已停止避免继续消耗Token"
    return ""


def _token_usage(data: dict[str, Any]) -> dict[str, int]:
    usage = data.get("usage") if isinstance(data, dict) else {}
    if not isinstance(usage, dict):
        return {}
    prompt_tokens = _int_token(usage.get("prompt_tokens"))
    completion_tokens = _int_token(usage.get("completion_tokens"))
    total_tokens = _int_token(usage.get("total_tokens"))
    if not total_tokens:
        total_tokens = prompt_tokens + completion_tokens
    result = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
    prompt_details = usage.get("prompt_tokens_details")
    completion_details = usage.get("completion_tokens_details")
    if isinstance(prompt_details, dict):
        result["cached_tokens"] = _int_token(prompt_details.get("cached_tokens"))
    if isinstance(completion_details, dict):
        result["reasoning_tokens"] = _int_token(completion_details.get("reasoning_tokens"))
    return result


def _sum_token_usage(steps: list[dict[str, Any]]) -> dict[str, int]:
    total: dict[str, int] = {}
    for step in steps:
        usage = step.get("token_usage") if isinstance(step, dict) else {}
        if not isinstance(usage, dict):
            continue
        for key, value in usage.items():
            amount = _int_token(value)
            if amount:
                total[key] = total.get(key, 0) + amount
    return total


def _int_token(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _mask_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _mask_value(key, _mask_sensitive(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_sensitive(item) for item in value]
    return value


def _mask_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return "******" if value not in (None, "") else value
    return value


def _is_sensitive_key(key: str) -> bool:
    return any(token in str(key).lower() for token in SENSITIVE_KEYS)


def _should_override_agent_value(value: str, key: str) -> bool:
    text = str(value or "").strip()
    return not text or text == "******" or (_is_sensitive_key(key) and len(text) > 8)


def _safe_timeout(value: Any, fallback: int) -> int:
    try:
        amount = int(value or fallback)
        if 0 < amount < 1000:
            amount *= 1000
        return min(max(amount, 0), 120000)
    except (TypeError, ValueError):
        return min(max(int(fallback or 1000), 0), 120000)


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


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "通过", "成功"}
    return bool(value)


def _max_steps(case: UiTestCase) -> int:
    try:
        return min(max(int(case.max_steps or 30), 1), 100)
    except (TypeError, ValueError):
        return 30


def _safe_page_title(page) -> str:
    try:
        return page.title()
    except Exception:
        return ""


def _cleanup_old_artifacts() -> None:
    if not ARTIFACT_ROOT.exists():
        return
    cutoff = datetime.now() - timedelta(days=ARTIFACT_RETENTION_DAYS)
    for path in ARTIFACT_ROOT.glob("*.png"):
        try:
            if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                path.unlink()
        except Exception:
            continue
