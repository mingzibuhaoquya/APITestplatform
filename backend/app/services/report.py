from html import escape
from typing import Any


def _status_class(status: str) -> str:
    if status == "passed":
        return "passed"
    if status in {"failed", "error"}:
        return "failed"
    return "running"


def _json_block(value: Any) -> str:
    return escape(str(value))


def build_html_report(task: Any, results: list[Any]) -> str:
    total = len(results)
    passed = sum(1 for item in results if item.status == "passed")
    failed = sum(1 for item in results if item.status in {"failed", "error"})
    rate = int((passed / total) * 100) if total else 0
    rows = []
    for index, result in enumerate(results, start=1):
        status_class = _status_class(result.status)
        assertions = "".join(
            f"<li class=\"{'passed' if item.get('passed') else 'failed'}\">"
            f"<span>{escape(str(item.get('type')))}</span>"
            f"<small>{escape(str(item.get('path') or ''))}</small>"
            f"<strong>{escape(str(item.get('actual') if item.get('actual') is not None else item.get('message') or '通过'))}</strong>"
            f"</li>"
            for item in result.assertion_results
        )
        rows.append(
            f"""
            <article class="case-card">
              <div class="case-head">
                <div><small>TEST CASE #{index}</small><h2>用例 {escape(str(result.case_id or '-'))}</h2></div>
                <span class="badge {status_class}">{escape(result.status)}</span>
              </div>
              <div class="meta"><span>耗时 {result.duration_ms} ms</span></div>
              <section><h3>Assertions</h3><ul class="assertions">{assertions or '<li>暂无断言</li>'}</ul></section>
              <section><h3>Request</h3><pre>{_json_block(result.request_snapshot)}</pre></section>
              <section><h3>Response</h3><pre>{_json_block(result.response_snapshot)}</pre></section>
            </article>
            """
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Allure Report - {escape(str(getattr(task, "id", "")))}</title>
  <style>
    body {{ margin: 0; background: #f6f8fb; color: #172033; font-family: Inter, Arial, 'Microsoft YaHei', sans-serif; }}
    .hero {{ background: #ffffff; border-bottom: 1px solid #e5e7eb; padding: 28px 36px; }}
    .hero h1 {{ margin: 0 0 8px; font-size: 26px; }}
    .hero p {{ margin: 0; color: #64748b; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 14px; padding: 20px 36px; }}
    .tile {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }}
    .tile span {{ display: block; color: #64748b; font-size: 12px; }}
    .tile strong {{ display: block; margin-top: 8px; font-size: 28px; }}
    main {{ padding: 0 36px 36px; }}
    .case-card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; margin: 14px 0; padding: 18px; }}
    .case-head {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; }}
    .case-head h2 {{ margin: 4px 0 0; font-size: 18px; }}
    .case-head small, .meta {{ color: #64748b; }}
    .badge {{ border-radius: 999px; padding: 4px 10px; font-weight: 700; font-size: 12px; }}
    .passed {{ color: #047857; background: #ecfdf5; }}
    .failed {{ color: #b91c1c; background: #fef2f2; }}
    .running {{ color: #b45309; background: #fffbeb; }}
    section h3 {{ margin: 18px 0 8px; font-size: 14px; }}
    .assertions {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }}
    .assertions li {{ display: grid; grid-template-columns: 180px 1fr 1fr; gap: 10px; padding: 8px 10px; border-radius: 6px; }}
    .assertions small {{ color: #64748b; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 6px; }}
  </style>
</head>
<body>
  <header class="hero">
    <h1>Allure Report</h1>
    <p>执行状态：{escape(task.status)}，任务编号：{escape(str(task.id))}</p>
  </header>
  <div class="summary">
    <div class="tile"><span>Total</span><strong>{total}</strong></div>
    <div class="tile"><span>Passed</span><strong>{passed}</strong></div>
    <div class="tile"><span>Failed</span><strong>{failed}</strong></div>
    <div class="tile"><span>Pass Rate</span><strong>{rate}%</strong></div>
  </div>
  <main>{''.join(rows)}</main>
</body>
</html>"""
