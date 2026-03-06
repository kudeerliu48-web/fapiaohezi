import asyncio
import os
from typing import Any, Dict, Optional

import httpx


BASE_URL = os.getenv("EXTERNAL_BATCH_BASE_URL", "http://14.103.188.30:1200")


class ExternalBatchApiError(RuntimeError):
    pass


async def submit_processed_input(*, batch_id: str, file_path: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/api/batches/processed-input"

    if not os.path.exists(file_path):
        raise ExternalBatchApiError(f"processed file not found: {file_path}")

    async with httpx.AsyncClient(timeout=300.0) as client:  # 5 分钟超时
        with open(file_path, "rb") as f:
            files = {"files": (os.path.basename(file_path), f, "image/webp")}
            data = {"batch_id": batch_id}
            resp = await client.post(url, data=data, files=files)
            if resp.status_code >= 400:
                raise ExternalBatchApiError(f"submit failed: {resp.status_code} {resp.text}")
            return resp.json()


async def run_batch(*, batch_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/api/batches/{batch_id}/run"
    async with httpx.AsyncClient(timeout=300.0) as client:  # 5 分钟超时
        resp = await client.post(url)
        if resp.status_code >= 400:
            raise ExternalBatchApiError(f"run failed: {resp.status_code} {resp.text}")
        return resp.json()


async def get_final_output(*, batch_id: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/api/batches/{batch_id}/final-output"
    async with httpx.AsyncClient(timeout=300.0) as client:  # 5 分钟超时
        resp = await client.get(url)
        if resp.status_code >= 400:
            raise ExternalBatchApiError(f"final-output failed: {resp.status_code} {resp.text}")
        return resp.json()


async def wait_final_output(*, batch_id: str, interval_s: float = 1.0, timeout_s: float = 300.0) -> Dict[str, Any]:  # 默认 5 分钟超时
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        payload = await get_final_output(batch_id=batch_id)
        status = payload.get("status")
        if status in {"completed", "failed"}:
            return payload
        if asyncio.get_event_loop().time() >= deadline:
            raise ExternalBatchApiError("final-output timeout")
        await asyncio.sleep(interval_s)
