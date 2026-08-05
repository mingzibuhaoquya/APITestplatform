import json
import re
from html import escape
from typing import Any


LOGO_PATH = "/company-logo.png"


def _status_class(status: str) -> str:
    if status == "passed":
        return "passed"
    if status in {"failed", "error"}:
        return "failed"
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
        rows.append(
            f"""
            <details class="case-card">
              <summary class="case-summary">
                <div class="case-title">
                  <h2>{escape(str(case_name))}</h2>
                  <p class="api-line"><span>接口</span>{escape(str(api_name))}</p>
                  <p class="url-line"><b>{escape(str(method))}</b>{escape(str(url))}</p>
                </div>
                <div class="case-right">
                  <span class="badge {row_status_class}">{escape(_status_label(result.status))}</span>
                  <span class="duration">{escape(str(result.duration_ms))} ms</span>
                </div>
              </summary>
              <div class="case-body">
                <section>
                  <h3>断言明细</h3>
                  <ul class="assertions">{_assertions_html(result.assertion_results)}</ul>
                </section>
                {_extractors_html(extracted_variables)}
                {_request_sections(request_snapshot, index)}
                {_response_sections(response_snapshot, index)}
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
    }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="brand">
      <img src="{LOGO_PATH}" alt="company logo" />
      <span>接口自动化测试平台</span>
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
  </script>
</body>
</html>"""
