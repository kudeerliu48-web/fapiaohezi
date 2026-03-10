import random
import threading
from datetime import datetime, timedelta
from typing import Dict

from fastapi import HTTPException

from config import config


class SMSService:
    """短信验证码服务（当前为可替换的开发占位实现）。"""

    def __init__(self):
        self._codes: Dict[str, dict] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _cache_key(phone: str, purpose: str) -> str:
        return f"{purpose}:{phone}"

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        return (phone or "").strip()

    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    def send_code(self, phone: str, purpose: str = "login") -> dict:
        phone = self._normalize_phone(phone)
        if not phone:
            raise HTTPException(status_code=400, detail="手机号不能为空")

        code = f"{random.randint(0, 999999):06d}"
        expire_at = self._now() + timedelta(seconds=config.SMS_CODE_EXPIRE_SECONDS)
        key = self._cache_key(phone, purpose)

        with self._lock:
            self._codes[key] = {
                "code": code,
                "expire_at": expire_at,
                "updated_at": self._now().isoformat(),
            }

        # 预留阿里云短信调用位置（开发环境使用 mock）
        if not config.SMS_MOCK_MODE:
            self._send_aliyun_sms(phone, code)

        payload = {
            "phone": phone,
            "purpose": purpose,
            "expire_seconds": config.SMS_CODE_EXPIRE_SECONDS,
            "sent_at": self._now().isoformat(),
        }
        if config.SMS_MOCK_MODE:
            payload["debug_code"] = code
        return payload

    def verify_code(self, phone: str, code: str, purpose: str = "login", consume: bool = True) -> bool:
        phone = self._normalize_phone(phone)
        key = self._cache_key(phone, purpose)

        with self._lock:
            record = self._codes.get(key)
            if not record:
                return False
            if self._now() > record["expire_at"]:
                self._codes.pop(key, None)
                return False
            if str(record["code"]) != str(code or ""):
                return False
            if consume:
                self._codes.pop(key, None)
            return True

    def _send_aliyun_sms(self, phone: str, code: str) -> None:
        """预留阿里云短信发送调用点。"""

        if not all([
            config.ALIYUN_SMS_ACCESS_KEY_ID,
            config.ALIYUN_SMS_ACCESS_KEY_SECRET,
            config.ALIYUN_SMS_SIGN_NAME,
            config.ALIYUN_SMS_TEMPLATE_CODE,
        ]):
            raise HTTPException(status_code=500, detail="阿里云短信配置缺失")

        # TODO: 在接入正式短信网关时于此处调用阿里云 SDK。
        # 当前保持占位，避免在开发环境误发短信。
        return


sms_service = SMSService()
