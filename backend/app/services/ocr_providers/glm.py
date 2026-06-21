"""GLM 云端视觉 OCR 适配器（OpenAI 兼容消息格式）。"""

import json
import logging
import re

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.services.ocr import extract_values
from app.services.ocr_providers.base import is_complete
from app.services.ocr_providers.temp_files import (
    create_temp_image,
    delete_temp_image,
)

logger = logging.getLogger(__name__)

GLM_OCR_UNAVAILABLE_MESSAGE = (
    "你的增强额度已耗完，请联系管理员进行充值继续使用"
)

SYSTEM_PROMPT = """你是血压计读数识别器。只读取血压计屏幕当前测量值，忽略日期、时间、用户编号和历史记录。
请返回严格 JSON，不要解释：
{"systolic": 收缩压整数或null, "diastolic": 舒张压整数或null, "heart_rate": 心率整数或null}
合理范围：收缩压50-260，舒张压30-180，心率30-220，且收缩压应大于舒张压。"""


def _extract_message_content(payload: dict) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("GLM 响应中缺少 message.content") from exc
    if isinstance(content, list):
        return " ".join(
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict)
        )
    return str(content)


def _parse_json_content(content: str) -> dict:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    else:
        matched = re.search(r"\{.*\}", text, re.S)
        if matched:
            text = matched.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = extract_values([content])

    result = {}
    ranges = {
        "systolic": (50, 260),
        "diastolic": (30, 180),
        "heart_rate": (30, 220),
    }
    aliases = {
        "systolic": ("systolic", "sys", "sbp", "high"),
        "diastolic": ("diastolic", "dia", "dbp", "low"),
        "heart_rate": ("heart_rate", "heartRate", "pulse", "pul", "pr"),
    }
    for field, names in aliases.items():
        value = next((data.get(name) for name in names if name in data), None)
        try:
            value = int(value) if value is not None else None
        except (TypeError, ValueError):
            value = None
        low, high = ranges[field]
        result[field] = value if value is not None and low <= value <= high else None
    return result


def _safe_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        error = payload.get("error", payload)
        code = error.get("code") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        if code or message:
            return f"{code or response.status_code}: {message or '请求失败'}"
    except (ValueError, TypeError):
        pass
    return f"HTTP {response.status_code}"


class GlmOcrProvider:
    name = "glm"

    async def recognize(self, content: bytes, content_type: str) -> dict:
        if not settings.glm_ocr_api_key:
            logger.warning("GLM-OCR unavailable: API Key is not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=GLM_OCR_UNAVAILABLE_MESSAGE,
            )
        if not settings.glm_ocr_endpoint or not settings.glm_ocr_model:
            logger.warning(
                "GLM-OCR unavailable: endpoint or model is not configured"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=GLM_OCR_UNAVAILABLE_MESSAGE,
            )
        if not settings.glm_ocr_public_base_url:
            logger.warning(
                "GLM-OCR unavailable: public temporary image URL is not configured"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=GLM_OCR_UNAVAILABLE_MESSAGE,
            )

        filename, temp_path = create_temp_image(content, content_type)
        public_base_url = settings.glm_ocr_public_base_url.rstrip("/")
        public_image_url = f"{public_base_url}/{filename}"
        payload = {
            "model": settings.glm_ocr_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "识别这张血压计照片。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": public_image_url
                            },
                        },
                    ],
                },
            ],
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {settings.glm_ocr_api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(settings.glm_ocr_timeout, connect=15)
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                response = await client.post(
                    settings.glm_ocr_endpoint,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                response_payload = response.json()
            raw_text = _extract_message_content(response_payload)
            values = _parse_json_content(raw_text)
        except httpx.HTTPStatusError as exc:
            detail = _safe_error_detail(exc.response)
            logger.warning("GLM-OCR HTTP error: %s", detail)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=GLM_OCR_UNAVAILABLE_MESSAGE,
            ) from exc
        except HTTPException as exc:
            logger.warning("GLM-OCR request rejected: %s", exc.detail)
            raise HTTPException(
                status_code=exc.status_code,
                detail=GLM_OCR_UNAVAILABLE_MESSAGE,
            ) from exc
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.warning("GLM-OCR request failed: %s: %s", type(exc).__name__, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=GLM_OCR_UNAVAILABLE_MESSAGE,
            ) from exc
        finally:
            delete_temp_image(temp_path)

        complete = is_complete(values)
        return {
            **values,
            "raw_text": [raw_text],
            "confidence": 0.90 if complete and values["heart_rate"] else (
                0.78 if complete else 0.40
            ),
            "complete": complete,
            "recognition_method": "glm_structured_vision",
            "engine": self.name,
            "provider": "glm",
            "requires_confirmation": True,
            "notice": "云端 AI 识别结果仅供录入参考，请核对数值后再保存。",
        }
