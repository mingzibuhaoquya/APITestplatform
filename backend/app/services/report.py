import json
import re
import base64
import mimetypes
from html import escape
from pathlib import Path
from typing import Any


LOGO_PATH = "/company-logo.png"
UI_ARTIFACT_ROOT = Path("logs/ui-artifacts")


def _status_class(status: str) -> str:
    if status == "passed":
        return "passed"
    if status in {"failed", "error"}:
        return "failed"
    if status == "stopped":
        return "running"
    return "running"


def _status_label(status: str) -> str:
    labels = {
        "passed": "通过",
        "failed": "失败",
        "error": "异常",
        "running": "运行中",
        "queued": "排队中",
    }
    return labels.get(status, status or "未知")


def _json_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)


def _display_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (dict, list)):
        return _json_text(value)
    return str(value)


def _time_text(value: Any) -> str:
    if not value:
        return "-"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _bool_text(value: Any) -> str:
    return "有头" if value is False else "无头"


def _ui_mode_text(mode: Any) -> str:
    return "AI模式" if mode == "ai" else "高级模式"


def _ui_action_text(action: Any) -> str:
    labels = {
        "goto": "打开页面",
        "click": "点击",
        "dblclick": "双击",
        "fill": "输入",
        "select": "选择",
        "wait": "等待",
        "assert_text": "断言文本",
        "assert_visible": "断言元素",
        "screenshot": "截图",
        "finish": "结束",
        "model_call": "模型调用",
        "error": "异常",
        "stopped": "已停止",
    }
    return labels.get(str(action or ""), str(action or "-"))


def _ui_locator_text(locator_type: Any) -> str:
    labels = {
        "css": "CSS",
        "xpath": "XPath",
        "text": "文本",
        "placeholder": "占位符",
        "role": "按钮文字",
        "ai": "AI描述",
    }
    return labels.get(str(locator_type or ""), str(locator_type or "-"))


def _token_usage_text(usage: Any, mode: Any = "ai") -> str:
    if mode != "ai":
        return "非AI模式不消耗Token"
    if not isinstance(usage, dict) or not usage:
        return "暂无记录，重新执行AI模式后生成"
    total = usage.get("total_tokens") or 0
    prompt = usage.get("prompt_tokens") or 0
    completion = usage.get("completion_tokens") or 0
    parts = [f"总计 {total}", f"输入 {prompt}", f"输出 {completion}"]
    if usage.get("reasoning_tokens"):
        parts.append(f"推理 {usage.get('reasoning_tokens')}")
    if usage.get("cached_tokens"):
        parts.append(f"缓存 {usage.get('cached_tokens')}")
    return " / ".join(parts)


def _xml_indent(level: int) -> str:
    return "    " * level


def _format_xml_text(text: str) -> str:
    source = text.strip()
    if not source:
        return ""
    tokens = re.findall(r"<!\[CDATA\[[\s\S]*?\]\]>|<!--[\s\S]*?-->|<\?[\s\S]*?\?>|<[^>]+>|[^<]+", source)
    if not tokens:
        raise ValueError("Invalid XML")
    rows: list[str] = []
    stack: list[str] = []
    level = 0
    index = 0
    while index < len(tokens):
        token = tokens[index].strip()
        index += 1
        if not token:
            continue
        if not token.startswith("<"):
            rows.append(f"{_xml_indent(level)}{token}")
            continue
        if token.startswith(("<?", "<!--", "<![CDATA[")):
            rows.append(f"{_xml_indent(level)}{token}")
            continue
        if token.startswith("</"):
            match = re.match(r"^</([A-Za-z_][\w.:-]*)\s*>$", token)
            expected = stack.pop() if stack else None
            if not match or expected != match.group(1):
                raise ValueError("Invalid XML")
            level = max(level - 1, 0)
            rows.append(f"{_xml_indent(level)}{token}")
            continue
        tag_match = re.match(r"^<([A-Za-z_][\w.:-]*)\b", token)
        if not tag_match:
            raise ValueError("Invalid XML")
        tag = tag_match.group(1)
        if token.endswith("/>"):
            rows.append(f"{_xml_indent(level)}{token}")
            continue
        next_index = index
        while next_index < len(tokens) and not tokens[next_index].strip():
            next_index += 1
        next_token = tokens[next_index].strip() if next_index < len(tokens) else ""
        close_token = tokens[next_index + 1].strip() if next_index + 1 < len(tokens) else ""
        if next_token == f"</{tag}>":
            rows.append(f"{_xml_indent(level)}{token[:-1]}/>")
            index = next_index + 1
            continue
        if next_token and not next_token.startswith("<") and close_token == f"</{tag}>":
            rows.append(f"{_xml_indent(level)}{token}{next_token}</{tag}>")
            index += 2
            continue
        rows.append(f"{_xml_indent(level)}{token}")
        stack.append(tag)
        level += 1
    if stack:
        raise ValueError("Invalid XML")
    return "\n".join(rows)


def _split_first_xml_document(text: str) -> tuple[str, str] | None:
    source = text.strip()
    match = re.search(r"<([A-Za-z_][\w.:-]*)\b[^>]*>", source)
    if not match:
        return None
    start_tag = match.group(0)
    root_tag = match.group(1)
    if start_tag.rstrip().endswith("/>"):
        return source[: match.end()], source[match.end() :].strip()
    close_tag = f"</{root_tag}>"
    close_index = source.find(close_tag, match.end())
    if close_index < 0:
        return None
    end_index = close_index + len(close_tag)
    return source[:end_index], source[end_index:].strip()


def _format_payload(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return _json_text(value)
    text = str(value).strip()
    if not text:
        return ""
    if text.startswith("<") or text.startswith("<?xml"):
        try:
            return _format_xml_text(text)
        except ValueError:
            split = _split_first_xml_document(text)
            if not split:
                return text
            xml, rest = split
            try:
                formatted = _format_xml_text(xml)
            except ValueError:
                return text
            return f"{formatted}\n{rest}" if rest else formatted
    try:
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    except (TypeError, ValueError, json.JSONDecodeError):
        return text


def _snapshot(title: str, value: Any, copy_id: str) -> str:
    return f"""
      <section class="snapshot">
        <div class="snapshot-title">
          <h3>{escape(title)}</h3>
          <button class="copy-btn" type="button" data-copy-target="{escape(copy_id)}" title="复制">复制</button>
        </div>
        <pre id="{escape(copy_id)}">{escape(_format_payload(value))}</pre>
      </section>
    """


def _request_sections(snapshot: dict[str, Any], index: int) -> str:
    if not snapshot:
        return _snapshot("请求快照", {}, f"request-{index}")
    sections = [
        _snapshot("请求头", snapshot.get("headers", {}), f"request-headers-{index}"),
        _snapshot("请求参数", snapshot.get("query", {}), f"request-query-{index}"),
    ]
    if "body_original" in snapshot:
        sections.append(_snapshot("请求原文", snapshot.get("body_original"), f"request-body-original-{index}"))
        if snapshot.get("sm3_signature"):
            sections.append(_snapshot("SM3签名", snapshot.get("sm3_signature"), f"request-sm3-signature-{index}"))
        sections.append(_snapshot("实际请求报文", snapshot.get("body"), f"request-body-{index}"))
    else:
        sections.append(_snapshot("请求报文", snapshot.get("body"), f"request-body-{index}"))
    return "".join(sections)


def _response_sections(snapshot: dict[str, Any], index: int) -> str:
    if not snapshot:
        return _snapshot("响应快照", {}, f"response-{index}")
    body = snapshot.get("decrypted_text")
    title = "响应解密报文" if body is not None else "响应报文"
    if body is None:
        body = snapshot.get("text")
    if body is None:
        body = snapshot.get("json")
    sections = [
        _snapshot("响应状态", {"status_code": snapshot.get("status_code"), "duration_ms": snapshot.get("duration_ms")}, f"response-meta-{index}"),
        _snapshot("响应头", snapshot.get("headers", {}), f"response-headers-{index}"),
        _snapshot(title, body, f"response-body-{index}"),
    ]
    if snapshot.get("encrypted_json") is not None:
        sections.insert(2, _snapshot("响应密文", snapshot.get("encrypted_json"), f"response-encrypted-{index}"))
    return "".join(sections)


def _assertions_html(assertions: list[dict]) -> str:
    if not assertions:
        return '<li class="muted-line">暂无断言</li>'
    rows = []
    for item in assertions:
        passed = bool(item.get("passed"))
        status_class = "passed" if passed else "failed"
        message = item.get("message") or ("通过" if passed else "失败")
        rows.append(
            f"""
            <li class="{status_class}">
              <span>{escape(str(item.get("type") or "-"))}</span>
              <small>{escape(str(item.get("path") or ""))}</small>
              <span><small>期望</small><strong>{escape(_display_value(item.get("expected")))}</strong></span>
              <span><small>实际</small><strong>{escape(_display_value(item.get("actual")))}</strong></span>
              <span><small>结果</small><strong>{escape(str(message))}</strong></span>
            </li>
            """
        )
    return "".join(rows)


def _extractors_html(extractors: list[dict]) -> str:
    if not extractors:
        return ""
    rows = []
    for item in extractors:
        success = bool(item.get("success"))
        status_class = "passed" if success else "failed"
        status_text = "成功" if success else "未提取"
        value = item.get("value")
        detail = "" if value is None else _json_text(value)
        rows.append(
            f"""
            <li class="{status_class}">
              <span>{escape(str(item.get("name") or "-"))}</span>
              <small>{escape(str(item.get("path") or ""))}</small>
              <strong>{escape(status_text)} {escape(str(detail))}</strong>
            </li>
            """
        )
    return f"""
      <section>
        <h3>参数提取结果</h3>
        <ul class="assertions extractors">{''.join(rows)}</ul>
      </section>
    """


def _is_ui_result(result: Any, request_snapshot: dict[str, Any], response_snapshot: dict[str, Any]) -> bool:
    return (
        getattr(result, "api_name", "") == "UI自动化"
        or request_snapshot.get("mode") == "ai"
        or "agent_steps" in response_snapshot
        or "steps" in response_snapshot and request_snapshot.get("browser")
    )


def _screenshot_path(path_text: str) -> Path | None:
    if not path_text:
        return None
    path = Path(path_text)
    candidates = [path]
    if not path.is_absolute():
        candidates.append(UI_ARTIFACT_ROOT / path.name)
    else:
        candidates.append(UI_ARTIFACT_ROOT / path.name)
    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _screenshot_src(path_text: str) -> str:
    path = _screenshot_path(path_text)
    if not path:
        filename = Path(path_text).name
        return f"/ui-artifacts/{escape(filename)}" if filename else ""
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        filename = path.name
        return f"/ui-artifacts/{escape(filename)}"
    return f"data:{mime_type};base64,{encoded}"


def _ui_base_info_html(task: Any, result: Any, request_snapshot: dict[str, Any], response_snapshot: dict[str, Any]) -> str:
    mode = request_snapshot.get("mode")
    items = [
        ("用例名称", getattr(result, "case_name", "") or "-"),
        ("项目", getattr(task, "project_name", "") or "-"),
        ("环境", (request_snapshot.get("environment") or {}).get("name") or getattr(task, "environment_name", "-")),
        ("执行人", getattr(task, "executor_name", "") or "-"),
        ("测试模式", _ui_mode_text(mode)),
        ("浏览器", request_snapshot.get("browser") or "chromium"),
        ("运行方式", _bool_text(request_snapshot.get("headless"))),
        ("目标地址", request_snapshot.get("start_url") or "-"),
        ("最大步骤数", request_snapshot.get("max_steps") or "-"),
        ("单步超时", f"{request_snapshot.get('step_timeout_ms') or '-'} ms"),
        ("开始时间", _time_text(getattr(task, "started_at", ""))),
        ("结束时间", _time_text(getattr(task, "ended_at", ""))),
    ]
    items.insert(6, ("Token消耗", _token_usage_text(response_snapshot.get("token_usage"), mode)))
    rows = "".join(f"<div><span>{escape(label)}</span><strong>{escape(_display_value(value))}</strong></div>" for label, value in items)
    return f"""
      <section>
        <h3>基础信息</h3>
        <div class="ui-info-grid">{rows}</div>
      </section>
    """


def _ui_steps_html(response_snapshot: dict[str, Any]) -> str:
    steps = response_snapshot.get("agent_steps") or response_snapshot.get("steps") or []
    if not steps:
        return """
          <section>
            <h3>步骤明细</h3>
            <p class="muted-line">暂无步骤记录</p>
          </section>
        """
    rows = []
    for fallback_index, item in enumerate(steps, start=1):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        status_class = _status_class(status)
        message = item.get("message") or item.get("reason") or item.get("description") or "-"
        target = item.get("target") or item.get("ref") or "-"
        value = item.get("value") or item.get("expected") or "-"
        rows.append(
            f"""
            <tr>
              <td>{escape(str(item.get("index") or fallback_index))}</td>
              <td>{escape(_ui_action_text(item.get("action")))}</td>
              <td>{escape(_ui_locator_text(item.get("locator_type")))}</td>
              <td class="wrap-cell">{escape(_display_value(target))}</td>
              <td class="wrap-cell">{escape(_display_value(value))}</td>
              <td><span class="badge {status_class}">{escape(_status_label(status))}</span></td>
              <td class="wrap-cell">{escape(_display_value(message))}</td>
            </tr>
            """
        )
    return f"""
      <section>
        <h3>步骤明细</h3>
        <div class="table-scroll">
          <table class="ui-step-report">
            <thead><tr><th>步骤</th><th>动作</th><th>定位方式</th><th>目标元素/地址</th><th>值/期望</th><th>状态</th><th>说明</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
          </table>
        </div>
      </section>
    """


def _ui_screenshots_html(response_snapshot: dict[str, Any]) -> str:
    screenshots = response_snapshot.get("screenshots") or []
    if not screenshots:
        return """
          <section>
            <h3>执行截图</h3>
            <p class="muted-line">暂无截图</p>
          </section>
        """
    cards = []
    for item in screenshots:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        src = _screenshot_src(path)
        if not src:
            continue
        title = f"步骤 {item.get('step_index') or '-'} · {item.get('type') or 'screenshot'}"
        cards.append(
            f"""
            <figure>
              <figcaption>{escape(title)}</figcaption>
              <button class="screenshot-preview" type="button" data-title="{escape(title, quote=True)}" title="点击查看截图">
                <img src="{escape(src, quote=True)}" alt="{escape(title, quote=True)}" />
              </button>
            </figure>
            """
        )
    if not cards:
        return """
          <section>
            <h3>执行截图</h3>
            <p class="muted-line">截图文件不存在或已被清理</p>
          </section>
        """
    return f"""
      <section>
        <h3>执行截图</h3>
        <div class="ui-screenshot-grid">{''.join(cards)}</div>
      </section>
    """


def _ui_result_html(task: Any, result: Any, request_snapshot: dict[str, Any], response_snapshot: dict[str, Any], index: int) -> str:
    test_goal = request_snapshot.get("test_goal")
    test_data = request_snapshot.get("test_data")
    assertion_goal = request_snapshot.get("assertion_goal")
    meta_sections = []
    if test_goal:
        meta_sections.append(_snapshot("测试目标", test_goal, f"ui-test-goal-{index}"))
    if test_data not in (None, {}, ""):
        meta_sections.append(_snapshot("测试数据", test_data, f"ui-test-data-{index}"))
    if assertion_goal:
        meta_sections.append(_snapshot("期望结果", assertion_goal, f"ui-assertion-goal-{index}"))
    error_message = getattr(result, "error_message", "") or response_snapshot.get("message") or ""
    error_analysis = response_snapshot.get("error_analysis") or ""
    error_html = _snapshot("错误信息", error_message or "-", f"ui-error-{index}") if error_message else ""
    analysis_html = _snapshot("AI分析", error_analysis, f"ui-error-analysis-{index}") if error_analysis else ""
    return f"""
      {_ui_base_info_html(task, result, request_snapshot, response_snapshot)}
      {''.join(meta_sections)}
      {_ui_steps_html(response_snapshot)}
      {_ui_screenshots_html(response_snapshot)}
      <section>
        <h3>断言结果</h3>
        <ul class="assertions">{_assertions_html(result.assertion_results)}</ul>
      </section>
      {analysis_html}
      {error_html}
    """


def build_html_report(task: Any, results: list[Any], target_name: str = "") -> str:
    total = len(results)
    passed = sum(1 for item in results if item.status == "passed")
    failed = sum(1 for item in results if item.status in {"failed", "error"})
    rate = int((passed / total) * 100) if total else 0
    plan_name = target_name or f"任务 {getattr(task, 'id', '')}"
    status_class = _status_class(getattr(task, "status", ""))
    rows = []
    for index, result in enumerate(results, start=1):
        row_status_class = _status_class(result.status)
        request_snapshot = result.request_snapshot if isinstance(result.request_snapshot, dict) else {}
        response_snapshot = result.response_snapshot if isinstance(result.response_snapshot, dict) else {}
        method = request_snapshot.get("method", "-")
        url = request_snapshot.get("url", "-")
        extracted_variables = response_snapshot.get("extracted_variables", [])
        case_name = getattr(result, "case_name", "") or f"用例 {result.case_id or '-'}"
        api_name = getattr(result, "api_name", "") or "-"
        if _is_ui_result(result, request_snapshot, response_snapshot):
            method = "UI"
            url = request_snapshot.get("start_url") or response_snapshot.get("url") or "-"
            api_name = "UI自动化"
            detail_html = _ui_result_html(task, result, request_snapshot, response_snapshot, index)
            subtitle = f"{_ui_mode_text(request_snapshot.get('mode'))} · {escape(str(url))}"
        else:
            detail_html = f"""
                <section>
                  <h3>断言明细</h3>
                  <ul class="assertions">{_assertions_html(result.assertion_results)}</ul>
                </section>
                {_extractors_html(extracted_variables)}
                {_request_sections(request_snapshot, index)}
                {_response_sections(response_snapshot, index)}
            """
            subtitle = f"<b>{escape(str(method))}</b>{escape(str(url))}"
        rows.append(
            f"""
            <details class="case-card">
              <summary class="case-summary">
                <div class="case-title">
                  <h2>{escape(str(case_name))}</h2>
                  <p class="api-line"><span>接口</span>{escape(str(api_name))}</p>
                  <p class="url-line">{subtitle}</p>
                </div>
                <div class="case-right">
                  <span class="badge {row_status_class}">{escape(_status_label(result.status))}</span>
                  <span class="duration">{escape(str(result.duration_ms))} ms</span>
                </div>
              </summary>
              <div class="case-body">
                {detail_html}
              </div>
            </details>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <base href="/" />
  <title>{escape(str(plan_name))}</title>
  <link rel="icon" href="{LOGO_PATH}" />
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #eef3f8; color: #172033; font-family: Inter, Arial, 'Microsoft YaHei', sans-serif; }}
    .hero {{ background: linear-gradient(135deg, #0f766e 0%, #2563eb 58%, #7c3aed 100%); color: #fff; padding: 30px 38px 36px; }}
    .brand {{ display: flex; align-items: center; gap: 12px; margin-bottom: 22px; }}
    .brand img {{ width: 34px; height: 34px; border-radius: 8px; background: #fff; padding: 4px; }}
    .brand span {{ font-weight: 700; }}
    .hero-content {{ display: flex; justify-content: space-between; gap: 24px; align-items: end; }}
    .hero h1 {{ margin: 0 0 10px; font-size: 30px; line-height: 1.2; }}
    .hero p {{ margin: 0; color: rgba(255,255,255,.82); }}
    .hero-status {{ display: grid; gap: 8px; justify-items: end; }}
    .status-pill {{ border-radius: 999px; padding: 7px 14px; background: rgba(255,255,255,.18); color: #fff; font-weight: 700; }}
    .status-pill.passed {{ background: rgba(22,163,74,.92); }}
    .status-pill.failed {{ background: rgba(220,38,38,.92); }}
    .status-pill.running {{ background: rgba(217,119,6,.92); }}
    .task-id {{ color: rgba(255,255,255,.75); font-size: 13px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 14px; padding: 20px 36px 10px; }}
    .tile {{ background: #fff; border: 1px solid #dfe7ef; border-radius: 10px; padding: 18px; box-shadow: 0 10px 30px rgba(15, 23, 42, .06); }}
    .tile span {{ display: block; color: #64748b; font-size: 12px; font-weight: 700; }}
    .tile strong {{ display: block; margin-top: 8px; font-size: 30px; }}
    .tile small {{ color: #94a3b8; }}
    main {{ padding: 6px 36px 38px; }}
    .section-title {{ display: flex; align-items: center; justify-content: space-between; margin: 16px 0 10px; }}
    .section-title h2 {{ margin: 0; font-size: 18px; }}
    .section-title span {{ color: #64748b; font-size: 13px; }}
    .case-card {{ background: #fff; border: 1px solid #dfe7ef; border-radius: 10px; margin: 12px 0; overflow: hidden; box-shadow: 0 8px 24px rgba(15, 23, 42, .05); }}
    .case-card[open] {{ border-color: #93c5fd; }}
    .case-summary {{ cursor: pointer; display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 16px 18px; }}
    .case-title {{ min-width: 0; }}
    .case-title h2 {{ margin: 0 0 8px; font-size: 18px; }}
    .case-title p {{ margin: 4px 0; color: #64748b; word-break: break-word; }}
    .api-line span {{ display: inline-block; margin-right: 8px; color: #2563eb; font-weight: 700; }}
    .url-line b {{ display: inline-block; margin-right: 8px; border-radius: 5px; padding: 2px 7px; background: #eff6ff; color: #1d4ed8; font-size: 12px; }}
    .case-right {{ display: flex; align-items: center; gap: 10px; white-space: nowrap; }}
    .duration {{ color: #64748b; font-size: 13px; }}
    .badge {{ border-radius: 999px; padding: 5px 11px; font-weight: 700; font-size: 12px; }}
    .badge.passed {{ color: #047857; background: #ecfdf5; }}
    .badge.failed {{ color: #b91c1c; background: #fef2f2; }}
    .badge.running {{ color: #b45309; background: #fffbeb; }}
    .case-body {{ border-top: 1px solid #e5e7eb; padding: 0 18px 18px; background: #fbfdff; }}
    section h3 {{ margin: 18px 0 8px; font-size: 14px; }}
    .assertions {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }}
    .assertions li {{ display: grid; grid-template-columns: 160px minmax(120px, 1fr) minmax(140px, 1fr) minmax(140px, 1fr) minmax(180px, 1.2fr); gap: 10px; padding: 9px 11px; border-radius: 7px; background: #fff; border: 1px solid #e5e7eb; }}
    .assertions.extractors li {{ grid-template-columns: 180px minmax(120px, 1fr) minmax(160px, 1.2fr); }}
    .assertions li.passed {{ border-left: 4px solid #16a34a; }}
    .assertions li.failed {{ border-left: 4px solid #dc2626; }}
    .assertions small {{ display: block; color: #64748b; }}
    .assertions strong {{ display: block; margin-top: 2px; word-break: break-word; }}
    .muted-line {{ color: #64748b; }}
    .ui-info-grid {{ display: grid; grid-template-columns: repeat(2, minmax(180px, 1fr)); gap: 10px; }}
    .ui-info-grid div {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 7px; padding: 10px 12px; min-width: 0; }}
    .ui-info-grid span {{ display: block; color: #64748b; font-size: 12px; margin-bottom: 5px; }}
    .ui-info-grid strong {{ display: block; word-break: break-word; font-size: 13px; }}
    .table-scroll {{ overflow-x: auto; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }}
    .ui-step-report {{ width: 100%; border-collapse: collapse; min-width: 980px; }}
    .ui-step-report th, .ui-step-report td {{ border-bottom: 1px solid #e5e7eb; padding: 10px 12px; text-align: left; vertical-align: top; font-size: 13px; }}
    .ui-step-report th {{ color: #334155; background: #f8fafc; font-weight: 700; }}
    .ui-step-report tr:last-child td {{ border-bottom: 0; }}
    .wrap-cell {{ word-break: break-word; max-width: 300px; }}
    .ui-screenshot-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }}
    .ui-screenshot-grid figure {{ margin: 0; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; overflow: hidden; }}
    .ui-screenshot-grid figcaption {{ padding: 9px 11px; color: #475569; font-size: 12px; border-bottom: 1px solid #e5e7eb; }}
    .screenshot-preview {{ display: block; width: 100%; padding: 0; border: 0; background: #f8fafc; cursor: zoom-in; }}
    .screenshot-preview img {{ display: block; width: 100%; max-height: 360px; object-fit: contain; background: #f8fafc; }}
    .report-lightbox {{ position: fixed; inset: 0; z-index: 999; display: none; align-items: center; justify-content: center; padding: 24px; }}
    .report-lightbox.open {{ display: flex; }}
    .report-lightbox-backdrop {{ position: absolute; inset: 0; background: rgba(15, 23, 42, .76); }}
    .report-lightbox-content {{ position: relative; z-index: 1; max-width: 96vw; max-height: 94vh; overflow: hidden; border-radius: 10px; background: #fff; box-shadow: 0 24px 80px rgba(15, 23, 42, .35); }}
    .report-lightbox-head {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; color: #334155; font-size: 13px; }}
    .report-lightbox-close {{ width: 30px; height: 30px; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; color: #475569; cursor: pointer; font-size: 18px; line-height: 1; }}
    .report-lightbox-close:hover {{ color: #2563eb; border-color: #93c5fd; background: #eff6ff; }}
    .report-lightbox img {{ display: block; max-width: 96vw; max-height: calc(94vh - 52px); object-fit: contain; background: #f8fafc; }}
    .snapshot-title {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
    .copy-btn {{ border: 1px solid #cbd5e1; background: #fff; color: #475569; border-radius: 7px; min-width: 44px; height: 30px; cursor: pointer; }}
    .copy-btn:hover {{ color: #2563eb; border-color: #93c5fd; background: #eff6ff; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #101827; color: #dbeafe; padding: 14px; border-radius: 8px; margin: 0; border: 1px solid #1e293b; }}
    @media (max-width: 900px) {{
      .hero {{ padding: 22px 16px; }}
      .hero-content {{ align-items: start; flex-direction: column; }}
      .hero-status {{ justify-items: start; }}
      .summary {{ grid-template-columns: 1fr 1fr; padding: 14px; }}
      main {{ padding: 6px 14px 24px; }}
      .case-summary {{ align-items: flex-start; flex-direction: column; }}
      .case-right {{ width: 100%; justify-content: space-between; }}
      .assertions li, .assertions.extractors li {{ grid-template-columns: 1fr; }}
      .ui-info-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="brand">
      <img src="{LOGO_PATH}" alt="company logo" />
      <span>测试平台</span>
    </div>
    <div class="hero-content">
      <div>
        <h1>测试执行报告</h1>
        <p>测试计划名称：{escape(str(plan_name))}</p>
      </div>
      <div class="hero-status">
        <span class="status-pill {status_class}">{escape(_status_label(task.status))}</span>
        <span class="task-id">任务 ID：{escape(str(task.id))}</span>
      </div>
    </div>
  </header>
  <div class="summary">
    <div class="tile total"><span>总用例数</span><strong>{total}</strong><small>Total</small></div>
    <div class="tile passed"><span>通过</span><strong>{passed}</strong><small>Passed</small></div>
    <div class="tile failed"><span>失败</span><strong>{failed}</strong><small>Failed</small></div>
    <div class="tile rate"><span>通过率</span><strong>{rate}%</strong><small>Pass Rate</small></div>
  </div>
  <main>
    <div class="section-title">
      <h2>用例明细</h2>
      <span>点击用例行展开请求、响应和断言详情</span>
    </div>
    {''.join(rows)}
  </main>
  <div class="report-lightbox" id="report-lightbox" aria-hidden="true">
    <div class="report-lightbox-backdrop" data-close-lightbox></div>
    <div class="report-lightbox-content" role="dialog" aria-modal="true" aria-label="截图预览">
      <div class="report-lightbox-head">
        <span id="report-lightbox-title">截图预览</span>
        <button class="report-lightbox-close" type="button" data-close-lightbox aria-label="关闭">×</button>
      </div>
      <img id="report-lightbox-image" alt="截图预览" />
    </div>
  </div>
  <script>
    document.querySelectorAll('.copy-btn').forEach(function(button) {{
      button.addEventListener('click', async function(event) {{
        event.preventDefault();
        event.stopPropagation();
        var target = document.getElementById(button.dataset.copyTarget);
        if (!target) return;
        try {{
          await navigator.clipboard.writeText(target.innerText);
          var oldText = button.textContent;
          button.textContent = '已复制';
          setTimeout(function() {{ button.textContent = oldText; }}, 900);
        }} catch (error) {{
          var range = document.createRange();
          range.selectNodeContents(target);
          var selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
        }}
      }});
    }});
    var lightbox = document.getElementById('report-lightbox');
    var lightboxImage = document.getElementById('report-lightbox-image');
    var lightboxTitle = document.getElementById('report-lightbox-title');
    function closeLightbox() {{
      if (!lightbox || !lightboxImage) return;
      lightbox.classList.remove('open');
      lightbox.setAttribute('aria-hidden', 'true');
      lightboxImage.removeAttribute('src');
    }}
    document.querySelectorAll('.screenshot-preview').forEach(function(button) {{
      button.addEventListener('click', function(event) {{
        event.preventDefault();
        event.stopPropagation();
        var image = button.querySelector('img');
        if (!lightbox || !lightboxImage || !image) return;
        lightboxImage.src = image.src;
        if (lightboxTitle) lightboxTitle.textContent = button.dataset.title || '截图预览';
        lightbox.classList.add('open');
        lightbox.setAttribute('aria-hidden', 'false');
      }});
    }});
    document.querySelectorAll('[data-close-lightbox]').forEach(function(element) {{
      element.addEventListener('click', closeLightbox);
    }});
    document.addEventListener('keydown', function(event) {{
      if (event.key === 'Escape') closeLightbox();
    }});
  </script>
</body>
</html>"""
