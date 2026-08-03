import json
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
    if status == "passed":
        return "通过"
    if status == "failed":
        return "失败"
    if status == "error":
        return "异常"
    if status == "running":
        return "运行中"
    if status == "queued":
        return "排队中"
    return status or "未知"


def _json_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)


def _json_block(value: Any) -> str:
    return escape(_json_text(value))


def _assertions_html(assertions: list[dict]) -> str:
    if not assertions:
        return '<li class="muted-line">暂无断言</li>'
    rows = []
    for item in assertions:
        passed = bool(item.get("passed"))
        status_class = "passed" if passed else "failed"
        actual = item.get("actual")
        detail = actual if actual is not None else item.get("message") or ("通过" if passed else "失败")
        rows.append(
            f"""
            <li class="{status_class}">
              <span>{escape(str(item.get("type") or "-"))}</span>
              <small>{escape(str(item.get("path") or ""))}</small>
              <strong>{escape(str(detail))}</strong>
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
        <ul class="assertions">{''.join(rows)}</ul>
      </section>
    """


def _snapshot(title: str, value: Any, copy_id: str) -> str:
    return f"""
      <section class="snapshot">
        <div class="snapshot-title">
          <h3>{escape(title)}</h3>
          <button class="copy-btn" type="button" data-copy-target="{escape(copy_id)}" title="复制">⧉</button>
        </div>
        <pre id="{escape(copy_id)}">{_json_block(value)}</pre>
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
        method = result.request_snapshot.get("method", "-") if isinstance(result.request_snapshot, dict) else "-"
        url = result.request_snapshot.get("url", "-") if isinstance(result.request_snapshot, dict) else "-"
        extracted_variables = result.response_snapshot.get("extracted_variables", []) if isinstance(result.response_snapshot, dict) else []
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
                {_snapshot("请求快照", result.request_snapshot, f"request-{index}")}
                {_snapshot("响应快照", result.response_snapshot, f"response-{index}")}
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
    .hero {{ position: relative; overflow: hidden; background: linear-gradient(135deg, #0f766e 0%, #2563eb 58%, #7c3aed 100%); color: #fff; padding: 30px 38px 36px; }}
    .hero::after {{ content: ''; position: absolute; right: -80px; top: -130px; width: 360px; height: 360px; border-radius: 50%; background: rgba(255,255,255,.14); }}
    .brand {{ position: relative; z-index: 1; display: flex; align-items: center; gap: 12px; margin-bottom: 22px; }}
    .brand img {{ width: 34px; height: 34px; border-radius: 8px; background: #fff; padding: 4px; }}
    .brand span {{ font-weight: 700; letter-spacing: .2px; }}
    .hero-content {{ position: relative; z-index: 1; display: flex; justify-content: space-between; gap: 24px; align-items: end; }}
    .hero h1 {{ margin: 0 0 10px; font-size: 30px; line-height: 1.2; }}
    .hero p {{ margin: 0; color: rgba(255,255,255,.82); }}
    .hero-status {{ display: grid; gap: 8px; justify-items: end; }}
    .status-pill {{ border-radius: 999px; padding: 7px 14px; background: rgba(255,255,255,.18); color: #fff; font-weight: 700; }}
    .status-pill.passed {{ background: rgba(22,163,74,.92); }}
    .status-pill.failed {{ background: rgba(220,38,38,.92); }}
    .status-pill.running {{ background: rgba(217,119,6,.92); }}
    .task-id {{ color: rgba(255,255,255,.75); font-size: 13px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 14px; padding: 20px 36px 10px; }}
    .tile {{ position: relative; overflow: hidden; background: #fff; border: 1px solid #dfe7ef; border-radius: 10px; padding: 18px; box-shadow: 0 10px 30px rgba(15, 23, 42, .06); }}
    .tile::before {{ content: ''; position: absolute; inset: 0 0 auto; height: 4px; background: #94a3b8; }}
    .tile.total::before {{ background: #2563eb; }}
    .tile.passed::before {{ background: #16a34a; }}
    .tile.failed::before {{ background: #dc2626; }}
    .tile.rate::before {{ background: #7c3aed; }}
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
    .case-summary::marker {{ color: #64748b; }}
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
    .assertions li {{ display: grid; grid-template-columns: 180px minmax(120px, 1fr) minmax(160px, 1.2fr); gap: 10px; padding: 9px 11px; border-radius: 7px; background: #fff; border: 1px solid #e5e7eb; }}
    .assertions li.passed {{ border-left: 4px solid #16a34a; }}
    .assertions li.failed {{ border-left: 4px solid #dc2626; }}
    .assertions small {{ color: #64748b; }}
    .muted-line {{ color: #64748b; }}
    .snapshot-title {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
    .copy-btn {{ border: 1px solid #cbd5e1; background: #fff; color: #475569; border-radius: 7px; width: 30px; height: 30px; cursor: pointer; line-height: 1; font-size: 16px; }}
    .copy-btn:hover {{ color: #2563eb; border-color: #93c5fd; background: #eff6ff; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #101827; color: #dbeafe; padding: 14px; border-radius: 8px; margin: 0; border: 1px solid #1e293b; }}
    @media (max-width: 760px) {{
      .hero {{ padding: 22px 16px; }}
      .hero-content {{ align-items: start; flex-direction: column; }}
      .hero-status {{ justify-items: start; }}
      .summary {{ grid-template-columns: 1fr 1fr; padding: 14px; }}
      main {{ padding: 6px 14px 24px; }}
      .case-summary {{ align-items: flex-start; flex-direction: column; }}
      .case-right {{ width: 100%; justify-content: space-between; }}
      .assertions li {{ grid-template-columns: 1fr; }}
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
          button.textContent = '✓';
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
