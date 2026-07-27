from html import escape
from typing import Any


def build_html_report(task: Any, results: list[Any]) -> str:
    rows = []
    for result in results:
        assertions = "".join(
            f"<li class=\"{'pass' if item.get('passed') else 'fail'}\">{escape(str(item.get('type')))} "
            f"{escape(str(item.get('path') or ''))}: {escape(str(item.get('message') or '通过'))}</li>"
            for item in result.assertion_results
        )
        rows.append(
            f"<section class=\"case\"><h3>用例 #{result.case_id or '-'} - {escape(result.status)}</h3>"
            f"<p>耗时：{result.duration_ms} ms</p><ul>{assertions}</ul>"
            f"<details><summary>请求</summary><pre>{escape(str(result.request_snapshot))}</pre></details>"
            f"<details><summary>响应</summary><pre>{escape(str(result.response_snapshot))}</pre></details></section>"
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>接口自动化测试报告 #{task.id}</title>
  <style>
    body {{ font-family: Arial, 'Microsoft YaHei', sans-serif; margin: 32px; color: #1f2937; }}
    header {{ border-bottom: 1px solid #d1d5db; margin-bottom: 24px; }}
    .case {{ border: 1px solid #d1d5db; border-radius: 6px; padding: 16px; margin: 16px 0; }}
    .pass {{ color: #047857; }}
    .fail {{ color: #b91c1c; }}
    pre {{ white-space: pre-wrap; background: #f3f4f6; padding: 12px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>接口自动化测试报告</h1>
    <p>任务 ID：{task.id}，状态：{escape(task.status)}</p>
  </header>
  {''.join(rows)}
</body>
</html>"""

