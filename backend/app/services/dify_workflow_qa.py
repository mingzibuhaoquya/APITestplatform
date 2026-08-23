import httpx

from ..config import get_settings


class DifyWorkflowQaError(RuntimeError):
    pass


def _api_url(api_base_url: str, path: str) -> str:
    base = (api_base_url or get_settings().dify_api_base_url).rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _headers(api_key: str) -> dict[str, str]:
    key = api_key.strip()
    if not key:
        raise DifyWorkflowQaError("Dify Workflow API Key 不能为空")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _outputs(payload: dict) -> dict:
    data = payload.get("data") if isinstance(payload, dict) else {}
    outputs = data.get("outputs") if isinstance(data, dict) else {}
    return outputs if isinstance(outputs, dict) else {}


def run_workflow(api_base_url: str, api_key: str, user_id: int, question: str, chat_history: str) -> dict:
    request_body = {
        "inputs": {
            "user_input": question,
            "chat_history": chat_history,
        },
        "response_mode": "blocking",
        "user": f"test-platform-{user_id}",
    }
    try:
        with httpx.Client(timeout=600) as client:
            response = client.post(_api_url(api_base_url, "workflows/run"), headers=_headers(api_key), json=request_body)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DifyWorkflowQaError(f"Dify 工作流调用失败: {exc}") from exc

    payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else {}
    if isinstance(data, dict) and data.get("status") not in {None, "succeeded"}:
        raise DifyWorkflowQaError(str(data.get("error") or data.get("status") or "Dify 工作流执行失败"))
    outputs = _outputs(payload)
    answer = str(outputs.get("result") or outputs.get("answer") or "").strip()
    if not answer:
        raise DifyWorkflowQaError("Dify 工作流未返回 result")
    return {
        "answer": answer,
        "workflow_run_id": str(payload.get("workflow_run_id") or (data.get("id") if isinstance(data, dict) else "") or ""),
        "task_id": str(payload.get("task_id") or ""),
        "outputs": outputs,
        "raw_response": payload,
    }
