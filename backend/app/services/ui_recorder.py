import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .ui_executor import DEFAULT_UI_LOCALE, DEFAULT_UI_USER_AGENT


SESSION_TTL_SECONDS = 10 * 60


PICKER_SCRIPT = r"""
(() => {
  if (window.__codexUiPickerInstalled) return;
  window.__codexUiPickerInstalled = true;
  window.__codexUiPickerArmed = false;
  window.__codexUiPickerResult = null;

  const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
  const quote = value => {
    const text = String(value || '');
    if (!text.includes("'")) return "'" + text + "'";
    if (!text.includes('"')) return '"' + text + '"';
    return "concat('" + text.replace(/'/g, "',\"'\",'") + "')";
  };
  const xpathLiteral = quote;
  const sameAttrCount = (name, value) => {
    if (!value) return 0;
    return document.evaluate(`count(//*[@${name}=${xpathLiteral(value)}])`, document, null, XPathResult.NUMBER_TYPE, null).numberValue;
  };
  const sameTextCount = text => {
    if (!text) return 0;
    return document.evaluate(`count(//*[normalize-space(.)=${xpathLiteral(text)}])`, document, null, XPathResult.NUMBER_TYPE, null).numberValue;
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
    if (id && sameAttrCount('id', id) === 1) return `//*[@id=${xpathLiteral(id)}]`;
    const name = el.getAttribute('name') || '';
    if (name && sameAttrCount('name', name) === 1) return `//*[@name=${xpathLiteral(name)}]`;
    const text = clean(el.innerText || el.textContent || el.value);
    if (text && text.length <= 60 && sameTextCount(text) === 1) {
      return `//*[normalize-space(.)=${xpathLiteral(text)}]`;
    }
    return absoluteXpath(el);
  };
  const elementSummary = el => ({
    tag: String(el.tagName || '').toLowerCase(),
    text: clean(el.innerText || el.textContent || el.value).slice(0, 120),
    id: el.id || '',
    name: el.getAttribute('name') || '',
    className: typeof el.className === 'string' ? el.className : '',
    type: el.getAttribute('type') || '',
    value: el.value || ''
  });
  const ensurePanel = () => {
    if (document.getElementById('__codex-ui-picker-panel')) return;
    const panel = document.createElement('div');
    panel.id = '__codex-ui-picker-panel';
    panel.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483647;background:#101828;color:#fff;border-radius:8px;padding:10px 12px;font:14px Arial;box-shadow:0 8px 24px rgba(15,23,42,.25);display:flex;gap:8px;align-items:center;';
    const label = document.createElement('span');
    label.id = '__codex-ui-picker-label';
    label.textContent = '元素拾取';
    const button = document.createElement('button');
    button.id = '__codex-ui-picker-arm';
    button.textContent = '开始拾取';
    button.style.cssText = 'border:0;border-radius:6px;background:#1677ff;color:#fff;padding:6px 10px;cursor:pointer;';
    button.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      window.__codexUiPickerArmed = true;
      label.textContent = '请点击目标元素';
      button.textContent = '拾取中...';
      button.style.background = '#d97706';
    }, true);
    panel.appendChild(label);
    panel.appendChild(button);
    document.documentElement.appendChild(panel);
  };
  const install = () => {
    ensurePanel();
    document.addEventListener('click', event => {
      const target = event.target;
      if (!window.__codexUiPickerArmed || !target || target.closest && target.closest('#__codex-ui-picker-panel')) return;
      event.preventDefault();
      event.stopPropagation();
      window.__codexUiPickerArmed = false;
      const selected = target.tagName && target.tagName.toLowerCase() === 'option' && target.parentElement ? target.parentElement : target;
      window.__codexUiPickerResult = {
        xpath: buildXpath(selected),
        summary: elementSummary(selected),
        page_url: location.href,
        page_title: document.title
      };
      const label = document.getElementById('__codex-ui-picker-label');
      const button = document.getElementById('__codex-ui-picker-arm');
      if (label) label.textContent = '已拾取';
      if (button) {
        button.textContent = '继续拾取';
        button.style.background = '#16a34a';
      }
      return false;
    }, true);
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, { once: true });
  } else {
    install();
  }
})();
"""


@dataclass
class RecorderSession:
    id: str
    url: str
    status: str = "starting"
    message: str = "正在启动浏览器"
    result: dict[str, Any] | None = None
    error: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    stop_event: threading.Event = field(default_factory=threading.Event)
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
        self._set_status(session, "closed", "拾取会话已关闭")
        return session

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
            browser = playwright.chromium.launch(headless=False)
            page = browser.new_page(
                user_agent=DEFAULT_UI_USER_AGENT,
                locale=DEFAULT_UI_LOCALE,
                viewport={"width": 1600, "height": 900},
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            )
            page.add_init_script(PICKER_SCRIPT)
            page.goto(session.url, wait_until="domcontentloaded", timeout=60000)
            self._inject_picker(page)
            self._set_status(session, "ready", "浏览器已打开，请在页面右下角点击“开始拾取”")
            last_url = page.url
            while not session.stop_event.is_set():
                try:
                    if page.url != last_url:
                        last_url = page.url
                        self._inject_picker(page)
                    picked = page.evaluate("window.__codexUiPickerResult || null")
                    if picked:
                        session.result = picked
                        page.evaluate("window.__codexUiPickerResult = null")
                        self._set_status(session, "picked", "元素已拾取，可继续拾取或关闭浏览器")
                except Exception:
                    if session.status not in {"closed", "error"}:
                        self._set_status(session, "closed", "浏览器已关闭")
                    break
                time.sleep(0.3)
        except Exception as exc:
            session.error = str(exc)
            self._set_status(session, "error", "启动拾取浏览器失败")
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

    def _inject_picker(self, page) -> None:
        try:
            page.evaluate(PICKER_SCRIPT)
        except Exception:
            pass

    def _set_status(self, session: RecorderSession, status: str, message: str) -> None:
        session.status = status
        session.message = message
        session.updated_at = datetime.now()


recorder_manager = UiRecorderManager()
