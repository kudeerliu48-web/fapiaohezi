"""V9 发票识别外部 API 客户端。

对接 V9 OCR 服务（http://182.92.151.50:12001/）。
支持两种模式：
  1. 批量模式：submit_batch → poll_status / get_items → get_results
  2. 单张兼容模式：submit_processed_input → run_batch → wait_final_output（旧接口保留）
"""

import asyncio
import mimetypes
import os
from typing import Any, Dict, List, Optional

import httpx

from config import config

# ── V9 API 地址 ──────────────────────────────────────────────

V9_BASE = config.V9_API_BASE_URL.rstrip("/")

# 旧版单张 API 地址（保留向后兼容）
LEGACY_BASE = os.getenv("EXTERNAL_BATCH_BASE_URL", "http://14.103.188.30:1200")


class ExternalBatchApiError(RuntimeError):
    pass


# ══════════════════════════════════════════════════════════════
#  V9 批量 API（推荐）
# ══════════════════════════════════════════════════════════════

async def v9_submit_batch(
    *,
    batch_id: str,
    file_paths: List[str],
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """V9 接口 1：提交批次（POST /api/invoices/submit）。

    Args:
        batch_id: 批次唯一 ID
        file_paths: 待识别的本地文件路径列表
        api_key: V9 API Key，为空时尝试从 config 获取

    Returns:
        V9 响应 data 字段，包含 batch_id, task_status, file_count 等
    """
    url = f"{V9_BASE}/api/invoices/submit"
    resolved_key = (api_key or config.V9_API_KEY or "").strip()

    files_payload: list = []
    for fp in file_paths:
        if not os.path.exists(fp):
            raise ExternalBatchApiError(f"文件不存在: {fp}")
        mime = mimetypes.guess_type(fp)[0] or "application/octet-stream"
        files_payload.append(("files", (os.path.basename(fp), open(fp, "rb"), mime)))

    data = {"batch_id": batch_id}
    if resolved_key:
        data["api_key"] = resolved_key

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(url, data=data, files=files_payload)
    finally:
        for _, (_, fobj, _) in files_payload:
            try:
                fobj.close()
            except Exception:
                pass

    if resp.status_code >= 400:
        raise ExternalBatchApiError(
            f"V9 submit 失败 [{resp.status_code}]: {resp.text}"
        )
    body = resp.json()
    if not body.get("success"):
        raise ExternalBatchApiError(
            f"V9 submit 业务失败: {body.get('message', resp.text)}"
        )
    return body.get("data", body)


async def v9_get_batch_status(*, batch_id: str) -> Dict[str, Any]:
    """V9 接口 3：查询批次状态（GET /api/invoices/batches/{batch_id}/status）。

    Returns:
        包含 status, total_files, completed_files, failed_files, pending_files, progress
    """
    url = f"{V9_BASE}/api/invoices/batches/{batch_id}/status"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
    if resp.status_code >= 400:
        raise ExternalBatchApiError(
            f"V9 status 失败 [{resp.status_code}]: {resp.text}"
        )
    body = resp.json()
    return body.get("data", body)


async def v9_get_batch_items(
    *, batch_id: str, since_id: int = 0
) -> Dict[str, Any]:
    """V9 接口 4：增量结果（GET /api/invoices/batches/{batch_id}/items）。

    Args:
        since_id: 上次已读取的最大 item_id，默认 0

    Returns:
        包含 items, has_more, next_since_id
    """
    url = f"{V9_BASE}/api/invoices/batches/{batch_id}/items"
    params = {"since_id": since_id}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
    if resp.status_code >= 400:
        raise ExternalBatchApiError(
            f"V9 items 失败 [{resp.status_code}]: {resp.text}"
        )
    body = resp.json()
    return body.get("data", body)


async def v9_get_batch_results(*, batch_id: str) -> Dict[str, Any]:
    """V9 接口 5：整批汇总（GET /api/invoices/batches/{batch_id}/results）。

    Returns:
        包含 items（全部结果数组）、status、success_files、failed_files
    """
    url = f"{V9_BASE}/api/invoices/batches/{batch_id}/results"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url)
    if resp.status_code >= 400:
        raise ExternalBatchApiError(
            f"V9 results 失败 [{resp.status_code}]: {resp.text}"
        )
    body = resp.json()
    return body.get("data", body)


async def v9_poll_until_done(
    *,
    batch_id: str,
    interval_s: Optional[float] = None,
    timeout_s: Optional[float] = None,
    on_progress: Any = None,
) -> Dict[str, Any]:
    """轮询 V9 批次状态直到全部完成，然后获取整批结果。

    Args:
        batch_id: 批次 ID
        interval_s: 轮询间隔，默认 config.V9_POLL_INTERVAL
        timeout_s: 超时时间，默认 config.V9_POLL_TIMEOUT
        on_progress: 可选回调 fn(status_data)，每次轮询到数据时调用

    Returns:
        V9 整批结果（同 v9_get_batch_results）
    """
    _interval = interval_s or config.V9_POLL_INTERVAL
    _timeout = timeout_s or config.V9_POLL_TIMEOUT

    loop = asyncio.get_event_loop()
    deadline = loop.time() + _timeout

    while True:
        status = await v9_get_batch_status(batch_id=batch_id)
        if callable(on_progress):
            try:
                on_progress(status)
            except Exception:
                pass

        batch_status = status.get("status", "")
        pending = int(status.get("pending_files", 1))
        if batch_status in ("completed", "partial_success", "failed") or pending == 0:
            break
        if loop.time() >= deadline:
            raise ExternalBatchApiError(
                f"V9 轮询超时 ({_timeout}s)，当前状态: {batch_status}"
            )
        await asyncio.sleep(_interval)

    return await v9_get_batch_results(batch_id=batch_id)


# ══════════════════════════════════════════════════════════════
#  旧版单张 API（保留向后兼容）
# ══════════════════════════════════════════════════════════════

async def submit_processed_input(*, batch_id: str, file_path: str) -> Dict[str, Any]:
    url = f"{LEGACY_BASE}/api/batches/processed-input"
    if not os.path.exists(file_path):
        raise ExternalBatchApiError(f"processed file not found: {file_path}")
    async with httpx.AsyncClient(timeout=300.0) as client:
        with open(file_path, "rb") as f:
            files = {"files": (os.path.basename(file_path), f, "image/webp")}
            data = {"batch_id": batch_id}
            resp = await client.post(url, data=data, files=files)
            if resp.status_code >= 400:
                raise ExternalBatchApiError(f"submit failed: {resp.status_code} {resp.text}")
            return resp.json()


async def run_batch(*, batch_id: str) -> Dict[str, Any]:
    url = f"{LEGACY_BASE}/api/batches/{batch_id}/run"
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(url)
        if resp.status_code >= 400:
            raise ExternalBatchApiError(f"run failed: {resp.status_code} {resp.text}")
        return resp.json()


async def get_final_output(*, batch_id: str) -> Dict[str, Any]:
    url = f"{LEGACY_BASE}/api/batches/{batch_id}/final-output"
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.get(url)
        if resp.status_code >= 400:
            raise ExternalBatchApiError(f"final-output failed: {resp.status_code} {resp.text}")
        return resp.json()


async def wait_final_output(*, batch_id: str, interval_s: float = 1.0, timeout_s: float = 300.0) -> Dict[str, Any]:
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        payload = await get_final_output(batch_id=batch_id)
        status = payload.get("status")
        if status in {"completed", "failed"}:
            return payload
        if asyncio.get_event_loop().time() >= deadline:
            raise ExternalBatchApiError("final-output timeout")
        await asyncio.sleep(interval_s)
