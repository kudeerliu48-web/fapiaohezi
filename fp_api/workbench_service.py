import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile

from config import config
from database import DatabaseManager, UserDatabaseManager
from external_batch_api import run_batch, submit_processed_input, wait_final_output
from image_processing import process_upload_to_pages
from utils import format_datetime, generate_uuid, init_user_database, safe_json_dumps, safe_json_loads


class WorkbenchService:
    STEP_ORDER = {
        "preprocess": 1,
        "ocr": 2,
        "normalize": 3,
        "validate": 4,
        "finalize": 5,
    }

    def __init__(self):
        self.main_db = DatabaseManager()

    def _ensure_user(self, user_id: str) -> None:
        if not self.main_db.get_user_by_id(user_id):
            raise HTTPException(status_code=404, detail="用户不存在")

    def _get_user_db_path(self, user_id: str) -> str:
        self._ensure_user(user_id)
        user_db_path = config.get_user_db_path(user_id)
        os.makedirs(os.path.dirname(user_db_path), exist_ok=True)
        init_user_database(user_id, user_db_path)
        return user_db_path

    def _write_debug_json(self, user_id: str, invoice_id: str, step_name: str, payload: Dict[str, Any]) -> None:
        debug_dir = config.get_debug_dir(user_id, invoice_id)
        os.makedirs(debug_dir, exist_ok=True)
        fp = os.path.join(debug_dir, f"{step_name}.json")
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _upsert_step(
        self,
        user_id: str,
        user_db_path: str,
        invoice_id: str,
        batch_id: Optional[str],
        step_name: str,
        status: str,
        input_payload: Optional[Dict[str, Any]] = None,
        output_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        debug_meta: Optional[Dict[str, Any]] = None,
        started_at: Optional[str] = None,
        ended_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = format_datetime()
        step = {
            "id": generate_uuid(),
            "invoice_id": invoice_id,
            "batch_id": batch_id,
            "step_name": step_name,
            "step_order": self.STEP_ORDER.get(step_name, 99),
            "status": status,
            "started_at": started_at or now,
            "ended_at": ended_at,
            "duration_ms": None,
            "input_payload": input_payload or {},
            "output_payload": output_payload or {},
            "error_message": error_message,
            "debug_meta": debug_meta or {},
            "created_at": now,
            "updated_at": now,
        }

        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO invoice_steps (
                id, invoice_id, batch_id, step_name, step_order, status,
                started_at, ended_at, duration_ms, input_payload, output_payload,
                error_message, debug_meta, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(invoice_id, step_name) DO UPDATE SET
                batch_id = excluded.batch_id,
                step_order = excluded.step_order,
                status = excluded.status,
                started_at = excluded.started_at,
                ended_at = excluded.ended_at,
                duration_ms = excluded.duration_ms,
                input_payload = excluded.input_payload,
                output_payload = excluded.output_payload,
                error_message = excluded.error_message,
                debug_meta = excluded.debug_meta,
                updated_at = excluded.updated_at
            """,
            (
                step["id"],
                step["invoice_id"],
                step["batch_id"],
                step["step_name"],
                step["step_order"],
                step["status"],
                step["started_at"],
                step["ended_at"],
                step["duration_ms"],
                safe_json_dumps(step["input_payload"]),
                safe_json_dumps(step["output_payload"]),
                step["error_message"],
                safe_json_dumps(step["debug_meta"]),
                step["created_at"],
                step["updated_at"],
            ),
        )
        conn.commit()
        conn.close()

        self._write_debug_json(user_id, invoice_id, step_name, step)
        return step

    def _mark_skipped_steps(self, user_id: str, user_db_path: str, invoice_id: str, batch_id: str, from_step: str, reason: str) -> None:
        start_order = self.STEP_ORDER.get(from_step, 99)
        for step_name, order in self.STEP_ORDER.items():
            if order > start_order:
                self._upsert_step(
                    user_id=user_id,
                    user_db_path=user_db_path,
                    invoice_id=invoice_id,
                    batch_id=batch_id,
                    step_name=step_name,
                    status="skipped",
                    output_payload={"reason": reason},
                    ended_at=format_datetime(),
                )

    def _batch_status(self, total: int, success: int, failed: int) -> str:
        processing = max(0, total - success - failed)
        if total == 0:
            return "empty"
        if processing > 0:
            return "processing"
        if success == total:
            return "completed"
        if failed == total:
            return "failed"
        return "partial_completed"

    def _refresh_batch(self, user_db_path: str, batch_id: str) -> None:
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN recognition_status = 1 THEN 1 ELSE 0 END) AS success,
                SUM(CASE WHEN recognition_status = 2 THEN 1 ELSE 0 END) AS failed,
                SUM(COALESCE(total_duration_ms, 0)) AS total_duration
            FROM invoice_details
            WHERE batch_id = ?
            """,
            (batch_id,),
        )
        row = cursor.fetchone()
        total = int(row["total"] or 0)
        success = int(row["success"] or 0)
        failed = int(row["failed"] or 0)
        total_duration = float(row["total_duration"] or 0)
        status = self._batch_status(total, success, failed)

        cursor.execute(
            """
            UPDATE batches
            SET status = ?, total_invoices = ?, success_count = ?, failed_count = ?,
                total_duration_ms = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, total, success, failed, total_duration, format_datetime(), batch_id),
        )
        conn.commit()
        conn.close()

    def _create_batch(self, user_db_path: str, user_id: str, remark: Optional[str] = None) -> str:
        batch_id = generate_uuid()
        now = format_datetime()
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO batches (
                id, user_id, status, total_invoices, success_count, failed_count,
                total_duration_ms, remark, created_at, updated_at
            ) VALUES (?, ?, ?, 0, 0, 0, 0, ?, ?, ?)
            """,
            (batch_id, user_id, "processing", remark, now, now),
        )
        conn.commit()
        conn.close()
        return batch_id

    async def upload_and_create_batch(
        self,
        user_id: str,
        files: List[UploadFile],
        remark: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not files:
            raise HTTPException(status_code=400, detail="请至少上传一个文件")

        user_db_path = self._get_user_db_path(user_id)
        batch_id = self._create_batch(user_db_path, user_id, remark=remark)

        created_invoices: List[Dict[str, Any]] = []
        failed_files: List[Dict[str, Any]] = []

        from services import file_service

        for upload in files:
            try:
                upload_result = await file_service.upload_file(user_id, upload, batch_id=batch_id)
                for page in upload_result.get("pages", []):
                    invoice_id = page["id"]
                    preprocess_output = {
                        "processed_filename": page.get("processed_filename"),
                        "processed_file_path": page.get("processed_file_path"),
                        "processed_width": page.get("processed_width"),
                        "processed_height": page.get("processed_height"),
                        "processed_bytes": page.get("processed_bytes"),
                        "page_index": page.get("page_index"),
                    }
                    self._upsert_step(
                        user_id=user_id,
                        user_db_path=user_db_path,
                        invoice_id=invoice_id,
                        batch_id=batch_id,
                        step_name="preprocess",
                        status="success",
                        input_payload={
                            "filename": upload_result.get("filename"),
                            "file_size": upload_result.get("file_size"),
                            "file_type": upload_result.get("file_type"),
                        },
                        output_payload=preprocess_output,
                        ended_at=format_datetime(),
                    )
                    created_invoices.append(page)
            except Exception as e:
                failed_files.append(
                    {
                        "filename": upload.filename,
                        "error_message": str(e),
                    }
                )

        if not created_invoices:
            conn = UserDatabaseManager.get_connection(user_db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM batches WHERE id = ?", (batch_id,))
            conn.commit()
            conn.close()
            first_error = failed_files[0]["error_message"] if failed_files else "上传失败"
            raise HTTPException(status_code=400, detail=f"上传失败：{first_error}")

        self._refresh_batch(user_db_path, batch_id)
        batch = self.get_batch_detail(user_id, batch_id)
        return {
            "batch": batch,
            "created_invoices": created_invoices,
            "failed_files": failed_files,
            "created_count": len(created_invoices),
            "failed_count": len(failed_files),
        }

    def _parse_amount(self, val: Any) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            raw = val.replace(",", "").strip()
            if not raw:
                return None
            try:
                return float(raw)
            except Exception:
                return None
        return None

    def _normalize_result(self, result_json: Dict[str, Any]) -> Dict[str, Any]:
        items = result_json.get("items") or []
        first_item = items[0] if items else {}
        return {
            "invoice_number": result_json.get("invoice_number"),
            "invoice_date": result_json.get("date") or result_json.get("invoice_date"),
            "buyer": result_json.get("buyer_name"),
            "seller": result_json.get("seller_name"),
            "service_name": first_item.get("item_name") or result_json.get("service_name"),
            "amount_without_tax": self._parse_amount(result_json.get("total_amount")),
            "tax_amount": self._parse_amount(result_json.get("total_tax")),
            "total_with_tax": self._parse_amount(result_json.get("total_amount_in_figures")) or self._parse_amount(result_json.get("total_amount")),
            "raw_result_json": result_json,
        }

    def _validate_and_repair(self, normalized: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        repaired = dict(normalized)
        warnings: List[str] = []

        if not repaired.get("invoice_number"):
            warnings.append("鍙戠エ鍙风爜缂哄け")

        if repaired.get("total_with_tax") is None:
            amount = repaired.get("amount_without_tax")
            tax = repaired.get("tax_amount")
            if amount is not None and tax is not None:
                repaired["total_with_tax"] = round(amount + tax, 2)
                warnings.append("浠风◣鍚堣缂哄け锛屽凡鐢遍噾棰?绋庨鎺ㄧ畻")

        return repaired, warnings

    def _get_invoice(self, user_db_path: str, invoice_id: str) -> Dict[str, Any]:
        invoice = UserDatabaseManager.get_invoice_by_id("", user_db_path, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="发票不存在")
        return invoice

    def _ensure_batch_for_invoice(self, user_db_path: str, user_id: str, invoice: Dict[str, Any]) -> str:
        batch_id = invoice.get("batch_id")
        if batch_id:
            return batch_id

        batch_id = self._create_batch(user_db_path, user_id, remark="历史数据自动补批次")
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE invoice_details SET batch_id = ?, updated_at = ? WHERE id = ?",
            (batch_id, format_datetime(), invoice["id"]),
        )
        conn.commit()
        conn.close()
        return batch_id

    def _mark_invoice_failed(self, user_db_path: str, invoice_id: str, error_message: str) -> None:
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE invoice_details
            SET recognition_status = 2,
                ocr_text = ?,
                final_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                error_message,
                safe_json_dumps({"error_message": error_message}),
                format_datetime(),
                invoice_id,
            ),
        )
        conn.commit()
        conn.close()

    async def rerun_invoice(self, user_id: str, invoice_id: str) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        invoice = self._get_invoice(user_db_path, invoice_id)
        batch_id = self._ensure_batch_for_invoice(user_db_path, user_id, invoice)
        pipeline_start = time.perf_counter()

        processed_filename = invoice.get("processed_filename")
        processed_path = os.path.join(config.get_processed_dir(user_id), processed_filename) if processed_filename else ""

        preprocess_started = format_datetime()
        if processed_filename and os.path.exists(processed_path):
            self._upsert_step(
                user_id=user_id,
                user_db_path=user_db_path,
                invoice_id=invoice_id,
                batch_id=batch_id,
                step_name="preprocess",
                status="success",
                input_payload={"mode": "reuse", "processed_filename": processed_filename},
                output_payload={"processed_file_path": f"/files/{user_id}/processed/{processed_filename}"},
                started_at=preprocess_started,
                ended_at=format_datetime(),
            )
        else:
            saved_filename = invoice.get("saved_filename")
            upload_path = os.path.join(config.get_upload_dir(user_id), saved_filename) if saved_filename else ""
            if not upload_path or not os.path.exists(upload_path):
                err = "预处理失败：找不到原始文件或预处理文件"
                self._upsert_step(
                    user_id=user_id,
                    user_db_path=user_db_path,
                    invoice_id=invoice_id,
                    batch_id=batch_id,
                    step_name="preprocess",
                    status="failed",
                    input_payload={"saved_filename": saved_filename},
                    error_message=err,
                    started_at=preprocess_started,
                    ended_at=format_datetime(),
                )
                self._mark_skipped_steps(user_id, user_db_path, invoice_id, batch_id, "preprocess", err)
                self._mark_invoice_failed(user_db_path, invoice_id, err)
                self._refresh_batch(user_db_path, batch_id)
                raise HTTPException(status_code=400, detail=err)

            try:
                regenerated = process_upload_to_pages(
                    upload_path=Path(upload_path),
                    original_filename=invoice.get("filename") or saved_filename,
                    processed_dir=Path(config.get_processed_dir(user_id)),
                    base_id=invoice_id,
                )
                page_index = int(invoice.get("page_index") or 1)
                selected = next((x for x in regenerated if int(x.get("page_index") or 1) == page_index), regenerated[0])
                processed_filename = selected.get("processed_filename")
                processed_path = os.path.join(config.get_processed_dir(user_id), processed_filename)

                conn = UserDatabaseManager.get_connection(user_db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE invoice_details
                    SET processed_filename = ?, processed_file_path = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (processed_filename, f"/files/{user_id}/processed/{processed_filename}", format_datetime(), invoice_id),
                )
                conn.commit()
                conn.close()

                self._upsert_step(
                    user_id=user_id,
                    user_db_path=user_db_path,
                    invoice_id=invoice_id,
                    batch_id=batch_id,
                    step_name="preprocess",
                    status="success",
                    input_payload={"mode": "rebuild", "saved_filename": saved_filename},
                    output_payload={
                        "processed_filename": processed_filename,
                        "processed_width": selected.get("processed_width"),
                        "processed_height": selected.get("processed_height"),
                        "processed_bytes": selected.get("processed_bytes"),
                    },
                    started_at=preprocess_started,
                    ended_at=format_datetime(),
                )
            except Exception as e:
                err = f"棰勫鐞嗗け璐ワ細{str(e)}"
                self._upsert_step(
                    user_id=user_id,
                    user_db_path=user_db_path,
                    invoice_id=invoice_id,
                    batch_id=batch_id,
                    step_name="preprocess",
                    status="failed",
                    input_payload={"saved_filename": saved_filename},
                    error_message=err,
                    started_at=preprocess_started,
                    ended_at=format_datetime(),
                )
                self._mark_skipped_steps(user_id, user_db_path, invoice_id, batch_id, "preprocess", err)
                self._mark_invoice_failed(user_db_path, invoice_id, err)
                self._refresh_batch(user_db_path, batch_id)
                raise HTTPException(status_code=500, detail=err)

        ocr_started = format_datetime()
        try:
            external_batch_id = f"{invoice_id}_{int(time.time())}"
            await submit_processed_input(batch_id=external_batch_id, file_path=processed_path)
            await run_batch(batch_id=external_batch_id)
            final_payload = await wait_final_output(batch_id=external_batch_id, interval_s=1.0, timeout_s=300.0)  # 5 鍒嗛挓瓒呮椂

            results = final_payload.get("results") or []
            first = (results[0] if results else {}) or {}
            result_json = first.get("result_json")
            if not isinstance(result_json, dict):
                raise RuntimeError("OCR杩斿洖涓虹┖")

            self._upsert_step(
                user_id=user_id,
                user_db_path=user_db_path,
                invoice_id=invoice_id,
                batch_id=batch_id,
                step_name="ocr",
                status="success",
                input_payload={"processed_filename": processed_filename},
                output_payload={
                    "external_batch_id": external_batch_id,
                    "total_time_ms": first.get("total_time_ms"),
                    "result_json": result_json,
                },
                started_at=ocr_started,
                ended_at=format_datetime(),
            )
        except Exception as e:
            err = f"OCR识别失败：{str(e)}"
            self._upsert_step(
                user_id=user_id,
                user_db_path=user_db_path,
                invoice_id=invoice_id,
                batch_id=batch_id,
                step_name="ocr",
                status="failed",
                input_payload={"processed_filename": processed_filename},
                error_message=err,
                started_at=ocr_started,
                ended_at=format_datetime(),
            )
            self._mark_skipped_steps(user_id, user_db_path, invoice_id, batch_id, "ocr", err)
            self._mark_invoice_failed(user_db_path, invoice_id, err)
            self._refresh_batch(user_db_path, batch_id)
            raise HTTPException(status_code=500, detail=err)

        normalize_started = format_datetime()
        normalized = self._normalize_result(result_json)
        self._upsert_step(
            user_id=user_id,
            user_db_path=user_db_path,
            invoice_id=invoice_id,
            batch_id=batch_id,
            step_name="normalize",
            status="success",
            input_payload={"result_json": result_json},
            output_payload=normalized,
            started_at=normalize_started,
            ended_at=format_datetime(),
        )

        validate_started = format_datetime()
        repaired, warnings = self._validate_and_repair(normalized)
        self._upsert_step(
            user_id=user_id,
            user_db_path=user_db_path,
            invoice_id=invoice_id,
            batch_id=batch_id,
            step_name="validate",
            status="success",
            input_payload=normalized,
            output_payload={"repaired": repaired, "warnings": warnings},
            started_at=validate_started,
            ended_at=format_datetime(),
        )

        finalize_started = format_datetime()
        total_duration_ms = round((time.perf_counter() - pipeline_start) * 1000, 2)
        final_json = {
            "normalized": repaired,
            "warnings": warnings,
            "raw_result_json": result_json,
        }

        from services import ocr_service

        await ocr_service.update_invoice_result(
            user_id,
            invoice_id,
            {
                "invoice_amount": repaired.get("total_with_tax"),
                "buyer": repaired.get("buyer"),
                "seller": repaired.get("seller"),
                "invoice_number": repaired.get("invoice_number"),
                "ocr_text": None,
                "json_info": repaired,
                "processing_time": total_duration_ms / 1000.0,
                "recognition_status": 1,
                "service_name": repaired.get("service_name"),
                "amount_without_tax": repaired.get("amount_without_tax"),
                "tax_amount": repaired.get("tax_amount"),
                "total_with_tax": repaired.get("total_with_tax"),
                "final_json": final_json,
                "total_duration_ms": total_duration_ms,
            },
        )

        self._upsert_step(
            user_id=user_id,
            user_db_path=user_db_path,
            invoice_id=invoice_id,
            batch_id=batch_id,
            step_name="finalize",
            status="success",
            input_payload={"repaired": repaired, "warnings": warnings},
            output_payload={"recognition_status": 1, "total_duration_ms": total_duration_ms},
            started_at=finalize_started,
            ended_at=format_datetime(),
        )

        self._refresh_batch(user_db_path, batch_id)
        return {
            "invoice": self.get_invoice_detail(user_id, invoice_id),
            "steps": self.get_invoice_steps(user_id, invoice_id),
        }

    async def rerun_batch(self, user_id: str, batch_id: str) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM invoice_details WHERE batch_id = ? ORDER BY upload_time DESC", (batch_id,))
        invoice_ids = [row["id"] for row in cursor.fetchall()]
        conn.close()

        if not invoice_ids:
            raise HTTPException(status_code=404, detail="批次下没有发票")

        success = 0
        failed = 0
        details: List[Dict[str, Any]] = []
        for invoice_id in invoice_ids:
            try:
                await self.rerun_invoice(user_id, invoice_id)
                details.append({"invoice_id": invoice_id, "status": "success"})
                success += 1
            except Exception as e:
                details.append({"invoice_id": invoice_id, "status": "failed", "error_message": str(e)})
                failed += 1

        self._refresh_batch(user_db_path, batch_id)
        return {"batch_id": batch_id, "success_count": success, "failed_count": failed, "results": details}

    def get_batches(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()

        where = ["user_id = ?"]
        params: List[Any] = [user_id]
        if status:
            where.append("status = ?")
            params.append(status)
        where_sql = " AND ".join(where)
        offset = (page - 1) * limit

        cursor.execute(
            f"""
            SELECT id, user_id, status, total_invoices, success_count, failed_count,
                   total_duration_ms, remark, created_at, updated_at
            FROM batches
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        batches = [dict(row) for row in cursor.fetchall()]

        cursor.execute(f"SELECT COUNT(*) AS total FROM batches WHERE {where_sql}", params)
        total = int(cursor.fetchone()["total"] or 0)
        conn.close()

        return {
            "batches": batches,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if limit else 1,
        }

    def get_batch_detail(self, user_id: str, batch_id: str) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        self._refresh_batch(user_db_path, batch_id)
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, status, total_invoices, success_count, failed_count,
                   total_duration_ms, remark, created_at, updated_at
            FROM batches
            WHERE id = ? AND user_id = ?
            """,
            (batch_id, user_id),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="批次不存在")

        batch = dict(row)
        try:
            from services import get_latest_recognition_job
            task_summary = get_latest_recognition_job(user_id, batch_id=batch_id)
            if task_summary.get("status") != "not_found":
                batch["task_summary"] = task_summary
        except Exception:
            pass
        return batch

    def get_batch_invoices(
        self,
        user_id: str,
        batch_id: str,
        page: int = 1,
        limit: int = 10,
        keyword: Optional[str] = None,
        recognition_status: Optional[int] = None,
    ) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        offset = (page - 1) * limit

        where = ["batch_id = ?"]
        params: List[Any] = [batch_id]
        if recognition_status is not None:
            where.append("recognition_status = ?")
            params.append(recognition_status)
        if keyword:
            like = f"%{keyword}%"
            where.append("(filename LIKE ? OR invoice_number LIKE ? OR buyer LIKE ? OR seller LIKE ?)")
            params.extend([like, like, like, like])
        where_sql = " AND ".join(where)

        cursor.execute(
            f"""
            SELECT id, batch_id, filename, saved_filename, processed_filename, color_filename, original_file_path, processed_file_path,
                   page_index, invoice_amount, buyer, seller, invoice_number, invoice_date, service_name,
                   amount_without_tax, tax_amount, total_with_tax, final_json, total_duration_ms,
                   recognition_status, processing_time, upload_time, file_type, file_size
            FROM invoice_details
            WHERE {where_sql}
            ORDER BY upload_time DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        invoices = [dict(row) for row in cursor.fetchall()]

        cursor.execute(f"SELECT COUNT(*) AS total FROM invoice_details WHERE {where_sql}", params)
        total = int(cursor.fetchone()["total"] or 0)
        conn.close()
        return {
            "invoices": invoices,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if limit else 1,
        }

    def get_invoice_history(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        keyword: Optional[str] = None,
        batch_id: Optional[str] = None,
        recognition_status: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        offset = (page - 1) * limit

        where = ["1=1"]
        params: List[Any] = []
        if batch_id:
            where.append("i.batch_id = ?")
            params.append(batch_id)
        if recognition_status is not None:
            where.append("i.recognition_status = ?")
            params.append(recognition_status)
        if keyword:
            like = f"%{keyword}%"
            where.append("(i.filename LIKE ? OR i.invoice_number LIKE ? OR i.buyer LIKE ? OR i.seller LIKE ?)")
            params.extend([like, like, like, like])
        if date_from:
            where.append("i.upload_time >= ?")
            params.append(date_from)
        if date_to:
            where.append("i.upload_time <= ?")
            params.append(date_to)

        where_sql = " AND ".join(where)
        cursor.execute(
            f"""
            SELECT
                i.id,
                i.id AS invoice_id,
                i.batch_id,
                i.filename,
                i.filename AS file_name,
                i.saved_filename, i.processed_filename, i.color_filename, i.original_file_path, i.processed_file_path,
                i.page_index, i.invoice_amount, i.buyer, i.seller, i.invoice_number, i.invoice_date, i.service_name,
                i.amount_without_tax, i.tax_amount, i.total_with_tax, i.final_json, i.total_duration_ms,
                i.recognition_status, i.processing_time, i.ocr_text AS error_message, i.upload_time, i.updated_at, i.file_type, i.file_size,
                i.buyer AS buyer_name, i.seller AS seller_name,
                b.status AS batch_status, b.created_at AS batch_created_at
            FROM invoice_details i
            LEFT JOIN batches b ON i.batch_id = b.id
            WHERE {where_sql}
            ORDER BY i.upload_time DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        rows = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM invoice_details i
            LEFT JOIN batches b ON i.batch_id = b.id
            WHERE {where_sql}
            """,
            params,
        )
        total = int(cursor.fetchone()["total"] or 0)
        conn.close()

        task_summary: Optional[Dict[str, Any]] = None
        try:
            from services import get_latest_recognition_job
            task_summary = get_latest_recognition_job(user_id, batch_id=batch_id)
        except Exception:
            task_summary = None

        if task_summary and task_summary.get("status") in {"queued", "running"}:
            current_invoice_id = task_summary.get("current_invoice_id")
            for row in rows:
                rec_status = row.get("recognition_status")
                if rec_status == 1:
                    row["runtime_status"] = "completed"
                elif rec_status == 2:
                    row["runtime_status"] = "failed"
                elif row.get("id") == current_invoice_id:
                    row["runtime_status"] = "running"
                else:
                    row["runtime_status"] = "queued"
        else:
            for row in rows:
                rec_status = row.get("recognition_status")
                if rec_status == 1:
                    row["runtime_status"] = "completed"
                elif rec_status == 2:
                    row["runtime_status"] = "failed"
                else:
                    row["runtime_status"] = "pending"

        for row in rows:
            row["status"] = row.get("runtime_status")

        return {
            "invoices": rows,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if limit else 1,
            "task_summary": task_summary,
        }

    def get_invoice_detail(self, user_id: str, invoice_id: str) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        invoice = self._get_invoice(user_db_path, invoice_id)
        invoice["invoice_id"] = invoice.get("id")
        invoice["file_name"] = invoice.get("filename")
        invoice["buyer_name"] = invoice.get("buyer")
        invoice["seller_name"] = invoice.get("seller")
        invoice["error_message"] = invoice.get("ocr_text")
        if invoice.get("final_json"):
            invoice["final_json"] = safe_json_loads(invoice["final_json"])
        if invoice.get("json_info"):
            invoice["json_info"] = safe_json_loads(invoice["json_info"])
        try:
            from services import get_latest_recognition_job
            task_summary = get_latest_recognition_job(user_id, batch_id=invoice.get("batch_id"))
            if task_summary.get("status") != "not_found":
                invoice["task_summary"] = task_summary
        except Exception:
            pass
        return invoice

    def get_invoice_steps(self, user_id: str, invoice_id: str) -> List[Dict[str, Any]]:
        try:
            user_db_path = self._get_user_db_path(user_id)
            conn = UserDatabaseManager.get_connection(user_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, invoice_id, batch_id, step_name, step_order, status, started_at, ended_at, duration_ms,
                       input_payload, output_payload, error_message, debug_meta, created_at, updated_at
                FROM invoice_steps
                WHERE invoice_id = ?
                ORDER BY step_order ASC
                """,
                (invoice_id,),
            )
            steps = [dict(row) for row in cursor.fetchall()]
            conn.close()
            for s in steps:
                s["input_payload"] = safe_json_loads(s.get("input_payload") or "{}")
                s["output_payload"] = safe_json_loads(s.get("output_payload") or "{}")
                s["debug_meta"] = safe_json_loads(s.get("debug_meta") or "{}")
            return steps
        except Exception as e:
            print(f"获取发票处理步骤失败：{e}")
            import traceback
            traceback.print_exc()
            raise

    def get_overview_stats(self, user_id: str) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS c FROM batches WHERE user_id = ?", (user_id,))
        total_batches = int(cursor.fetchone()["c"] or 0)

        cursor.execute("SELECT COUNT(*) AS c FROM invoice_details")
        total_invoices = int(cursor.fetchone()["c"] or 0)

        cursor.execute("SELECT COUNT(*) AS c FROM invoice_details WHERE recognition_status = 0")
        processing_count = int(cursor.fetchone()["c"] or 0)

        cursor.execute("SELECT COUNT(*) AS c FROM invoice_details WHERE recognition_status = 1")
        success_count = int(cursor.fetchone()["c"] or 0)

        cursor.execute("SELECT COUNT(*) AS c FROM invoice_details WHERE recognition_status = 2")
        failed_count = int(cursor.fetchone()["c"] or 0)

        today_prefix = format_datetime()[:10]
        cursor.execute("SELECT COUNT(*) AS c FROM invoice_details WHERE upload_time LIKE ?", (f"{today_prefix}%",))
        today_new = int(cursor.fetchone()["c"] or 0)

        cursor.execute("SELECT AVG(total_duration_ms) AS avg_ms FROM invoice_details WHERE total_duration_ms IS NOT NULL AND total_duration_ms > 0")
        avg_ms_row = cursor.fetchone()
        avg_duration_ms = float(avg_ms_row["avg_ms"] or 0)

        conn.close()
        return {
            "total_batches": total_batches,
            "total_invoices": total_invoices,
            "processing_count": processing_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "today_new": today_new,
            "avg_duration_ms": round(avg_duration_ms, 2),
        }

    def _remove_invoice_debug_dir(self, user_id: str, invoice_id: str) -> None:
        debug_dir = config.get_debug_dir(user_id, invoice_id)
        if os.path.exists(debug_dir):
            shutil.rmtree(debug_dir, ignore_errors=True)

    def delete_invoice(self, user_id: str, invoice_id: str) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        invoice = self._get_invoice(user_db_path, invoice_id)
        batch_id = invoice.get("batch_id")

        from services import file_service
        file_service.delete_invoice(user_id, invoice_id)

        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoice_steps WHERE invoice_id = ?", (invoice_id,))
        conn.commit()
        conn.close()

        self._remove_invoice_debug_dir(user_id, invoice_id)
        if batch_id:
            self._refresh_batch(user_db_path, batch_id)
        return {"deleted": True}

    def delete_batch(self, user_id: str, batch_id: str) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM invoice_details WHERE batch_id = ?", (batch_id,))
        invoice_ids = [row["id"] for row in cursor.fetchall()]
        conn.close()

        from services import file_service

        deleted_invoices = 0
        if invoice_ids:
            result = file_service.batch_delete_invoices(user_id, invoice_ids)
            deleted_invoices = int(result.get("deleted") or 0)

        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoice_steps WHERE batch_id = ?", (batch_id,))
        cursor.execute("DELETE FROM batches WHERE id = ?", (batch_id,))
        conn.commit()
        conn.close()

        for invoice_id in invoice_ids:
            self._remove_invoice_debug_dir(user_id, invoice_id)

        return {"deleted": True, "deleted_invoices": deleted_invoices}

    def clear_all_history(self, user_id: str) -> Dict[str, Any]:
        user_db_path = self._get_user_db_path(user_id)
        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM invoice_details")
        invoice_ids = [row["id"] for row in cursor.fetchall()]
        cursor.execute("SELECT COUNT(*) AS c FROM batches")
        batch_total = int(cursor.fetchone()["c"] or 0)
        conn.close()

        from services import file_service

        deleted_invoices = 0
        if invoice_ids:
            result = file_service.batch_delete_invoices(user_id, invoice_ids)
            deleted_invoices = int(result.get("deleted") or 0)

        conn = UserDatabaseManager.get_connection(user_db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoice_steps")
        cursor.execute("DELETE FROM batches")
        conn.commit()
        conn.close()

        debug_root = config.get_debug_dir(user_id)
        if os.path.exists(debug_root):
            shutil.rmtree(debug_root, ignore_errors=True)

        return {"deleted_invoices": deleted_invoices, "deleted_batches": batch_total}


workbench_service = WorkbenchService()

