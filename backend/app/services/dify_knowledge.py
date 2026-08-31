from time import perf_counter
from typing import Any

import httpx

from ..config import get_settings


class DifyKnowledgeError(RuntimeError):
    pass


def _api_url(path: str) -> str:
    return f"{get_settings().dify_api_base_url.rstrip('/')}/{path.lstrip('/')}"


def _headers() -> dict[str, str]:
    api_key = get_settings().dify_knowledge_api_key.strip()
    if not api_key:
        raise DifyKnowledgeError("Dify Knowledge API Key is not configured")
    return {"Authorization": f"Bearer {api_key}"}


def _document_out(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "name": str(item.get("name") or item.get("filename") or ""),
        "indexing_status": str(item.get("indexing_status") or item.get("status") or ""),
        "enabled": bool(item.get("enabled", True)),
        "word_count": item.get("word_count") or item.get("tokens") or 0,
        "hit_count": item.get("hit_count") or 0,
        "create_date": item.get("created_at") or item.get("create_date") or "",
        "update_date": item.get("updated_at") or item.get("update_date") or "",
    }


def _dataset_out(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "name": str(item.get("name") or ""),
        "description": str(item.get("description") or ""),
        "document_count": item.get("document_count") or item.get("documents_count") or 0,
        "word_count": item.get("word_count") or 0,
        "create_date": item.get("created_at") or item.get("create_date") or "",
        "update_date": item.get("updated_at") or item.get("update_date") or "",
    }


def _hit_out(item: dict[str, Any]) -> dict[str, Any]:
    segment = item.get("segment") if isinstance(item.get("segment"), dict) else item
    document = item.get("document") if isinstance(item.get("document"), dict) else segment.get("document") if isinstance(segment, dict) else {}
    segment = segment if isinstance(segment, dict) else {}
    document = document if isinstance(document, dict) else {}
    return {
        "content": str(segment.get("content") or item.get("content") or ""),
        "score": item.get("score") or segment.get("score") or 0,
        "document_id": str(document.get("id") or segment.get("document_id") or item.get("document_id") or ""),
        "document_name": str(document.get("name") or document.get("filename") or item.get("document_name") or ""),
        "segment_id": str(segment.get("id") or item.get("segment_id") or item.get("id") or ""),
        "position": segment.get("position") or item.get("position") or 0,
    }


def list_datasets(keyword: str = "", page: int = 1, page_size: int = 100) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "limit": page_size}
    if keyword.strip():
        params["keyword"] = keyword.strip()
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(_api_url("datasets"), headers=_headers(), params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DifyKnowledgeError(f"Dify 知识库列表查询失败: {exc}") from exc

    payload = response.json()
    rows = payload.get("data") if isinstance(payload.get("data"), list) else payload.get("datasets") or []
    if not isinstance(rows, list):
        rows = []
    return {
        "items": [_dataset_out(item) for item in rows if isinstance(item, dict)],
        "total": payload.get("total") or len(rows),
        "page": payload.get("page") or page,
        "page_size": payload.get("limit") or payload.get("page_size") or page_size,
    }


def list_documents(dataset_id: str, keyword: str = "", status: str = "", page: int = 1, page_size: int = 10) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "limit": page_size}
    if keyword.strip():
        params["keyword"] = keyword.strip()
    if status.strip():
        params["status"] = status.strip()
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(_api_url(f"datasets/{dataset_id}/documents"), headers=_headers(), params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DifyKnowledgeError(f"Dify 文档列表查询失败: {exc}") from exc

    payload = response.json()
    rows = payload.get("data") if isinstance(payload.get("data"), list) else payload.get("documents") or []
    if not isinstance(rows, list):
        rows = []
    return {
        "items": [_document_out(item) for item in rows if isinstance(item, dict)],
        "total": payload.get("total") or len(rows),
        "page": payload.get("page") or page,
        "page_size": payload.get("limit") or payload.get("page_size") or page_size,
    }


def retrieve(dataset_id: str, query: str, top_k: int, score_threshold: float | None) -> tuple[dict[str, Any], int]:
    retrieval_model: dict[str, Any] = {
        "search_method": "semantic_search",
        "reranking_enable": False,
        "top_k": top_k,
        "score_threshold_enabled": score_threshold is not None,
    }
    if score_threshold is not None:
        retrieval_model["score_threshold"] = score_threshold

    started = perf_counter()
    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                _api_url(f"datasets/{dataset_id}/retrieve"),
                headers={**_headers(), "Content-Type": "application/json"},
                json={"query": query, "retrieval_model": retrieval_model},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DifyKnowledgeError(f"Dify 知识库检索失败: {exc}") from exc
    duration_ms = int((perf_counter() - started) * 1000)

    payload = response.json()
    records = payload.get("records") or payload.get("data") or []
    if isinstance(records, dict):
        records = records.get("records") or records.get("items") or []
    if not isinstance(records, list):
        records = []
    hits = [_hit_out(item) for item in records if isinstance(item, dict)]
    return {"query": query, "hits": hits, "raw_status": payload.get("status") or ""}, duration_ms


def check_dataset(dataset_id: str) -> dict[str, Any]:
    result = list_documents(dataset_id, page=1, page_size=1)
    return {"ok": True, "document_count": result["total"]}
