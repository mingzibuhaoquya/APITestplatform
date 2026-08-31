import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .ui_executor import DEFAULT_UI_LOCALE, DEFAULT_UI_USER_AGENT


SESSION_TTL_SECONDS = 10 * 60
VIEWPORT = {"width": 1366, "height": 1050}


PICK_SCRIPT = r"""
([x, y]) => {
  const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
  const quote = value => {
    const text = String(value || '');
    if (!text.includes("'")) return "'" + text + "'";
    if (!text.includes('"')) return '"' + text + '"';
    return "concat('" + text.replace(/'/g, "',\"'\",'") + "')";
  };
  const sameAttrCount = (name, value) => {
    if (!value) return 0;
    return document.evaluate(`count(//*[@${name}=${quote(value)}])`, document, null, XPathResult.NUMBER_TYPE, null).numberValue;
  };
  const sameTextCount = text => {
    if (!text) return 0;
    return document.evaluate(`count(//*[normalize-space(.)=${quote(text)}])`, document, null, XPathResult.NUMBER_TYPE, null).numberValue;
  };
  const segment = el => {
    const tag = el.tagName.toLowerCase();
    if (!el.parentElement) return tag;
    const siblings = Array.from(el.parentElement.children).filter(item => item.tagName === el.tagName);
    if (siblings.length === 1) return tag;
    return `${tag}[${siblings.indexOf(el) + 1}]`;
  };
  const absoluteXpath = el => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1) {
      parts.unshift(segment(node));
      node = node.parentElement;
    }
    return '/' + parts.join('/');
  };
  const buildXpath = target => {
    let el = target;
    if (el && el.tagName && el.tagName.toLowerCase() === 'option' && el.parentElement) {
      el = el.parentElement;
    }
    const id = el.id || '';
    if (id && sameAttrCount('id', id) === 1) return `//*[@id=${quote(id)}]`;
    const name = el.getAttribute('name') || '';
    if (name && sameAttrCount('name', name) === 1) return `//*[@name=${quote(name)}]`;
    const text = clean(el.innerText || el.textContent || el.value);
    if (text && text.length <= 60 && sameTextCount(text) === 1) {
      return `//*[normalize-space(.)=${quote(text)}]`;
    }
    return absoluteXpath(el);
  };
  const selectOptions = el => {
    if (!el || String(el.tagName || '').toLowerCase() !== 'select') return [];
    return Array.from(el.options || []).map(option => ({
      value: option.value || '',
      label: clean(option.label || option.textContent || option.value),
      selected: !!option.selected
    }));
  };
  const elementSummary = el => ({
    tag: String(el.tagName || '').toLowerCase(),
    text: clean(el.innerText || el.textContent || el.value).slice(0, 120),
    id: el.id || '',
    name: el.getAttribute('name') || '',
    className: typeof el.className === 'string' ? el.className : '',
    type: el.getAttribute('type') || '',
    value: el.value || '',
    options: selectOptions(el)
  });
  const target = document.elementFromPoint(x, y);
  if (!target || target === document.documentElement || target === document.body) {
    return null;
  }
  const selected = target.tagName && target.tagName.toLowerCase() === 'option' && target.parentElement ? target.parentElement : target;
  return {
    xpath: buildXpath(selected),
    summary: elementSummary(selected),
    page_url: location.href,
    page_title: document.title
  };
}
"""


@dataclass
class RecorderCommand:
    action: str
    payload: dict[str, Any] = field(default_factory=dict)
    done: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: str = ""


@dataclass
class RecorderSession:
    id: str
    url: str
    status: str = "starting"
    message: str = "正在启动远程浏览器"
    result: dict[str, Any] | None = None
    error: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    stop_event: threading.Event = field(default_factory=threading.Event)
    commands: queue.Queue[RecorderCommand] = field(default_factory=queue.Queue)
    thread: threading.Thread | None = None


class UiRecorderManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, RecorderSession] = {}

    def create_session(self, url: str) -> RecorderSession:
        self.cleanup_expired()
        session = RecorderSession(id=uuid.uuid4().hex, url=url)
        thread = threading.Thread(target=self._run_session, args=(session,), daemon=True)
        session.thread = thread
        with self._lock:
            self._sessions[session.id] = session
        thread.start()
        return session

    def get_session(self, session_id: str) -> RecorderSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> RecorderSession | None:
        session = self.get_session(session_id)
        if not session:
            return None
        session.stop_event.set()
        try:
            self.run_command(session, "close", {}, timeout=2)
            message = "远程浏览器已关闭"
        except RuntimeError:
            message = "远程浏览器关闭请求已提交，后台正在清理"
        with self._lock:
            self._sessions.pop(session_id, None)
        self._set_status(session, "closed", message)
        return session

    def run_command(self, session: RecorderSession, action: str, payload: dict[str, Any] | None = None, timeout: int = 15) -> Any:
        if session.status in {"closed", "error"} and action != "close":
            raise RuntimeError(session.error or session.message or "拾取会话不可用")
        command = RecorderCommand(action=action, payload=payload or {})
        session.commands.put(command)
        if not command.done.wait(timeout):
            raise RuntimeError("远程浏览器操作超时")
        if command.error:
            raise RuntimeError(command.error)
        return command.result

    def cleanup_expired(self) -> None:
        now = time.time()
        expired: list[str] = []
        with self._lock:
            for session_id, session in self._sessions.items():
                if now - session.created_at.timestamp() > SESSION_TTL_SECONDS:
                    session.stop_event.set()
                    expired.append(session_id)
            for session_id in expired:
                self._sessions.pop(session_id, None)

    def _run_session(self, session: RecorderSession) -> None:
        browser = None
        playwright = None
        try:
            from playwright.sync_api import sync_playwright

            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=DEFAULT_UI_USER_AGENT,
                locale=DEFAULT_UI_LOCALE,
                viewport=VIEWPORT,
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            )
            page.goto(session.url, wait_until="domcontentloaded", timeout=60000)
            self._set_status(session, "ready", "远程浏览器已打开，可在截图上操作或拾取元素")
            while not session.stop_event.is_set():
                try:
                    command = session.commands.get(timeout=0.3)
                except queue.Empty:
                    continue
                self._handle_command(page, command, session)
        except Exception as exc:
            session.error = _friendly_error(str(exc))
            self._set_status(session, "error", "远程浏览器启动失败")
        finally:
            try:
                if browser:
                    browser.close()
            except Exception:
                pass
            try:
                if playwright:
                    playwright.stop()
            except Exception:
                pass

    def _handle_command(self, page, command: RecorderCommand, session: RecorderSession) -> None:
        try:
            action = command.action
            payload = command.payload
            if action == "screenshot":
                command.result = page.screenshot(type="png", full_page=False)
            elif action == "click":
                page.mouse.click(float(payload.get("x", 0)), float(payload.get("y", 0)))
                page.wait_for_timeout(500)
                command.result = {"ok": True}
            elif action == "pick":
                result = page.evaluate(PICK_SCRIPT, [float(payload.get("x", 0)), float(payload.get("y", 0))])
                if not result:
                    raise RuntimeError("当前位置未识别到可拾取元素")
                session.result = result
                self._set_status(session, "picked", "元素已拾取，可继续操作或关闭会话")
                command.result = result
            elif action == "type":
                page.keyboard.type(str(payload.get("text", "")), delay=20)
                page.wait_for_timeout(200)
                command.result = {"ok": True}
            elif action == "press":
                page.keyboard.press(str(payload.get("key", "Enter")))
                page.wait_for_timeout(300)
                command.result = {"ok": True}
            elif action == "select":
                xpath = str(payload.get("xpath", "")).strip()
                value = str(payload.get("value", ""))
                label = str(payload.get("label", ""))
                if not xpath:
                    raise RuntimeError("请先拾取下拉框")
                locator = page.locator(f"xpath={xpath}")
                selected = False
                try:
                    locator.select_option(value)
                    selected = True
                except Exception:
                    if label:
                        locator.select_option(label=label)
                        selected = True
                if not selected:
                    raise RuntimeError(f"选择下拉项失败：{label or value}")
                locator.dispatch_event("input")
                locator.dispatch_event("change")
                locator.dispatch_event("blur")
                page.wait_for_timeout(500)
                command.result = {"ok": True}
            elif action == "close":
                session.stop_event.set()
                command.result = {"ok": True}
            else:
                raise RuntimeError(f"不支持的远程浏览器操作: {action}")
        except Exception as exc:
            command.error = _friendly_error(str(exc))
        finally:
            command.done.set()

    def _set_status(self, session: RecorderSession, status: str, message: str) -> None:
        session.status = status
        session.message = message
        session.updated_at = datetime.now()


def _friendly_error(message: str) -> str:
    text = str(message or "")
    if "net::ERR" in text:
        return "远程浏览器无法访问目标地址，请检查服务器网络是否能访问该系统"
    return text


recorder_manager = UiRecorderManager()
