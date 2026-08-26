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
from .ui_executor import (
    ARTIFACT_ROOT,
    DEFAULT_UI_LOCALE,
    DEFAULT_UI_USER_AGENT,
    UiResultView,
    _goto_and_wait,
    _save_artifacts,
    _save_result,
    build_ui_url,
)


ALLOWED_AGENT_ACTIONS = {"click", "fill", "select", "wait", "assert_text", "screenshot", "finish"}
SENSITIVE_KEYS = ("password", "passwd", "secret", "token", "key", "密码", "密钥", "令牌")
ARTIFACT_RETENTION_DAYS = 7


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

    setting = db.query(AiSetting).first()
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
            browser = playwright.chromium.launch(headless=case.headless is not False)
            page = browser.new_page(
                user_agent=DEFAULT_UI_USER_AGENT,
                locale=DEFAULT_UI_LOCALE,
                viewport={"width": 1600, "height": 900},
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            )
            try:
                current_url = build_ui_url(env, case.start_url or "/")
                _goto_and_wait(page, current_url, case)
                for index in range(1, _max_steps(case) + 1):
                    observation = observe_page(page)
                    decision = decide_next_action(setting, case, observation, agent_steps)
                    result = run_agent_action(page, decision, observation, index, case)
                    result["url"] = page.url
                    result["page_title"] = _safe_page_title(page)
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
        error_message = str(exc)
        agent_steps.append({"index": len(agent_steps) + 1, "action": "error", "status": "error", "message": error_message})
        _update_task_progress(db, task, agent_steps, screenshots, "error", error_message)

    duration_ms = int((time.perf_counter() - started) * 1000)
    row = _save_result(
        db,
        task.id,
        case.id,
        final_status,
        _agent_request_snapshot(case, env, current_url),
        {"agent_steps": agent_steps, "screenshots": screenshots},
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
        "可用动作：click、fill、select、wait、assert_text、screenshot、finish。"
        "必须只使用current_page.candidates中当前可见可操作元素的ref字段，不要复用history里的旧ref或旧XPath。"
        "不要对disabled/不可编辑控件执行fill/select/click；不要请求打开外部网址；不确定时使用wait或finish失败。"
        "返回格式：{\"action\":\"click|fill|select|wait|assert_text|screenshot|finish\","
        "\"ref\":\"e1\",\"value\":\"\",\"reason\":\"\",\"success\":true,\"message\":\"\"}。"
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
    return normalize_agent_decision(content)


def _post_chat_completion(url: str, payload: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 400 and payload.get("response_format"):
            retry_payload = {key: value for key, value in payload.items() if key != "response_format"}
            retry_response = httpx.post(url, json=retry_payload, headers=headers, timeout=30)
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
                "hint": "请检查模型服务地址、网络连通性、代理和服务器 DNS。",
            },
        ) from exc


def normalize_agent_decision(content: str | dict[str, Any]) -> dict[str, Any]:
    data: Any = content
    if isinstance(content, str):
        text = content.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.S)
            if not match:
                raise RuntimeError("AI未返回可识别的JSON动作")
            data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise RuntimeError("AI动作必须是JSON对象")
    action = str(data.get("action") or "").strip()
    if action not in ALLOWED_AGENT_ACTIONS:
        raise RuntimeError(f"AI返回了不支持的动作：{action or '-'}")
    return {
        "action": action,
        "ref": str(data.get("ref") or "").strip(),
        "target": str(data.get("target") or data.get("selector") or "").strip(),
        "locator_type": str(data.get("locator_type") or "xpath").strip(),
        "value": str(data.get("value") or ""),
        "reason": str(data.get("reason") or ""),
        "success": _as_bool(data.get("success")) if action == "finish" else False,
        "message": str(data.get("message") or ""),
    }


def run_agent_action(page, decision: dict[str, Any], observation: dict[str, Any], index: int, case: UiTestCase) -> dict[str, Any]:
    action = decision["action"]
    result = {
        "index": index,
        "action": action,
        "ref": decision.get("ref", ""),
        "target": decision.get("target", ""),
        "value": _mask_value("value", decision.get("value", "")),
        "reason": decision.get("reason", ""),
        "status": "passed",
        "message": decision.get("message") or "通过",
    }
    try:
        if not case.allow_ai_actions and action in {"click", "fill", "select"}:
            raise RuntimeError("当前用例未允许AI自主点击/输入")
        if action == "finish":
            result["success"] = bool(decision.get("success"))
            result["status"] = "passed" if result["success"] else "failed"
            result["message"] = decision.get("message") or ("AI判定用例通过" if result["success"] else "AI判定用例失败")
            return result
        if action == "wait":
            timeout = _safe_timeout(decision.get("value"), case.step_timeout_ms)
            page.wait_for_timeout(timeout)
            result["message"] = f"已等待 {timeout}ms"
            return result
        if action == "screenshot":
            result["message"] = "已截图"
            return result
        if action == "assert_text":
            expected = decision.get("value") or decision.get("target") or ""
            visible = page.get_by_text(str(expected)).first.is_visible(timeout=case.step_timeout_ms)
            result["assertion"] = {"type": "ui_agent_assert_text", "path": str(expected), "expected": "可见", "actual": "可见" if visible else "不可见", "passed": visible, "message": "通过" if visible else "未找到文本"}
            if not visible:
                result["status"] = "failed"
                result["message"] = f"未找到文本：{expected}"
            return result
        resolved_target = _target_from_ref(decision, observation)
        result["locator_type"] = resolved_target.get("locator_type", "xpath")
        result["target"] = resolved_target.get("target", result.get("target", ""))
        locator = _locator_for_target(page, resolved_target)
        if action == "click":
            locator.click(timeout=case.step_timeout_ms)
            _settle_page(page, case.step_timeout_ms)
            page.wait_for_timeout(1500)
        elif action == "fill":
            locator.fill(str(decision.get("value") or ""), timeout=case.step_timeout_ms)
        elif action == "select":
            value = str(decision.get("value") or "")
            try:
                locator.select_option(value, timeout=case.step_timeout_ms)
            except Exception:
                locator.select_option(label=value, timeout=case.step_timeout_ms)
            locator.dispatch_event("input")
            locator.dispatch_event("change")
            locator.dispatch_event("blur")
            _settle_page(page, min(case.step_timeout_ms, 5000))
            page.wait_for_timeout(800)
        page.wait_for_timeout(500)
    except Exception as exc:
        result["status"] = "error"
        result["message"] = str(exc)
    return result


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
        "browser": "chromium",
        "headless": case.headless is not False,
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


def _mask_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _mask_value(key, _mask_sensitive(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_sensitive(item) for item in value]
    return value


def _mask_value(key: str, value: Any) -> Any:
    if any(token in str(key).lower() for token in SENSITIVE_KEYS):
        return "******" if value not in (None, "") else value
    return value


def _safe_timeout(value: Any, fallback: int) -> int:
    try:
        return min(max(int(value or fallback), 0), 120000)
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
