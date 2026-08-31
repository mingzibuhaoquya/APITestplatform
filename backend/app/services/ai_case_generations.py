from datetime import datetime
import mimetypes
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from uuid import uuid4

import httpx

from ..config import get_settings
from ..database import SessionLocal
from ..models import AiCaseGeneration
from ..utils import dump_json, parse_json


class DifyGenerationError(RuntimeError):
    pass


def _dify_headers() -> dict[str, str]:
    api_key = get_settings().dify_workflow_api_key.strip()
    if not api_key:
        raise DifyGenerationError("Dify Workflow API Key is not configured")
    return {"Authorization": f"Bearer {api_key}"}


def _api_url(path: str) -> str:
    return f"{get_settings().dify_api_base_url.rstrip('/')}/{path.lstrip('/')}"


async def upload_source_document(filename: str, content: bytes, content_type: str, user_id: int) -> str:
    if not content:
        raise DifyGenerationError("上传文件不能为空")
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                _api_url("files/upload"),
                headers=_dify_headers(),
                data={"user": f"test-platform-{user_id}"},
                files={"file": (filename, content, content_type or "application/octet-stream")},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DifyGenerationError(f"Dify 文档上传失败: {exc}") from exc

    payload = response.json()
    file_id = str(payload.get("id") or "").strip()
    if not file_id:
        raise DifyGenerationError("Dify 文档上传未返回文件标识")
    return file_id


def _storage_dir() -> Path:
    path = Path(get_settings().ai_generation_storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_filename(value: str, fallback: str) -> str:
    name = Path(value or "").name.strip() or fallback
    return "".join(char if char not in '\\/:*?\"<>|' else "_" for char in name)[:180]


def _download_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        return urljoin(f"{get_settings().dify_api_base_url.rstrip('/')}/", raw_url)
    base = urlparse(get_settings().dify_api_base_url)
    return urlunparse(parsed._replace(scheme=base.scheme, netloc=base.netloc))


def _download_output_files(payload: dict) -> list[dict]:
    outputs = ((payload.get("data") or {}).get("outputs") or {})
    files = outputs.get("files")
    if not isinstance(files, list) or not files:
        raise DifyGenerationError("Dify 工作流未返回生成文件")

    stored_files: list[dict] = []
    try:
        with httpx.Client(timeout=120) as client:
            for index, file_item in enumerate(files, start=1):
                if not isinstance(file_item, dict):
                    raise DifyGenerationError("Dify 返回的生成文件格式无效")
                raw_url = str(file_item.get("url") or "").strip()
                if not raw_url:
                    raise DifyGenerationError("Dify 返回的生成文件缺少下载地址")
                download_url = _download_url(raw_url)
                try:
                    response = client.get(download_url, headers=_dify_headers())
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    raise DifyGenerationError(f"生成文件下载失败: {exc}") from exc

                filename = _safe_filename(str(file_item.get("filename") or file_item.get("name") or ""), f"测试用例_{index}.xlsx")
                storage_name = f"{uuid4().hex}_{filename}"
                target = _storage_dir() / storage_name
                target.write_bytes(response.content)
                stored_files.append({
                    "name": filename,
                    "storage_name": storage_name,
                    "size": len(response.content),
                    "content_type": response.headers.get("content-type") or mimetypes.guess_type(filename)[0] or "application/octet-stream",
                })
    except Exception:
        for item in stored_files:
            (_storage_dir() / item["storage_name"]).unlink(missing_ok=True)
        raise
    return stored_files


def execute_ai_case_generation(generation_id: int) -> None:
    db = SessionLocal()
    try:
        row = db.get(AiCaseGeneration, generation_id)
        if not row:
            return
        row.status = "running"
        row.started_at = row.started_at or datetime.now()
        row.error_message = ""
        db.commit()

        request_body = {
            "inputs": {
                "upload_document": [{
                    "transfer_method": "local_file",
                    "upload_file_id": row.dify_file_id,
                    "type": "document",
                }],
            },
            "response_mode": "blocking",
            "user": f"test-platform-{row.creator_id}",
        }
        try:
            with httpx.Client(timeout=600) as client:
                response = client.post(_api_url("workflows/run"), headers={**_dify_headers(), "Content-Type": "application/json"}, json=request_body)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DifyGenerationError(f"Dify 工作流调用失败: {exc}") from exc

        payload = response.json()
        data = payload.get("data") or {}
        if data.get("status") not in {None, "succeeded"}:
            raise DifyGenerationError(str(data.get("error") or data.get("status") or "Dify 工作流执行失败"))
        output_files = _download_output_files(payload)

        row.workflow_run_id = str(payload.get("workflow_run_id") or data.get("id") or "")
        row.output_files_json = dump_json(output_files)
        row.status = "succeeded"
        row.ended_at = datetime.now()
        db.commit()
    except Exception as exc:
        db.rollback()
        row = db.get(AiCaseGeneration, generation_id)
        if row:
            row.status = "failed"
            row.error_message = str(exc)[:4000]
            row.ended_at = datetime.now()
            db.commit()
    finally:
        db.close()


def generation_files(row: AiCaseGeneration) -> list[dict]:
    files = parse_json(row.output_files_json, [])
    return files if isinstance(files, list) else []
