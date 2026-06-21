"""豆包视觉模型血压计识别适配器。"""

import base64
import json
import logging
import re

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.services.ocr_providers.base import is_complete
from app.services.ocr_providers.temp_files import normalize_image_to_jpeg

logger = logging.getLogger(__name__)

DOUBAO_OCR_UNAVAILABLE_MESSAGE = "豆包增强识别暂不可用，请稍后重试"

DOUBAO_PROMPT = """请识别血压计屏幕上当前测量结果，只返回 JSON 对象。
字段：
- systolic：SYS/SBP/收缩压/高压，整数，合理范围 50-260
- diastolic：DIA/DBP/舒张压/低压，整数，合理范围 30-180
- heart_rate：PUL/PR/BPM/心率/脉搏，整数，合理范围 30-220

必须遵守：
1. 只读取屏幕当前测量值，忽略日期、时间、用户编号、记忆编号和历史记录。
2. 收缩压必须大于舒张压。
3. 看不清的字段返回 null，禁止猜测或补造。
4. 不要解释，不要 Markdown，只返回：
{"systolic": null, "diastolic": null, "heart_rate": null}"""

FIELD_RANGES = {
    "systolic": (50, 260),
    "diastolic": (30, 180),
    "heart_rate": (30, 220),
}


def _extract_json_object(content: str) -> dict:
    text = str(content).strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    else:
        matched = re.search(r"\{.*\}", text, re.S)
        if matched:
            text = matched.group(0)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("豆包响应不是有效 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("豆包响应 JSON 不是对象")
    return payload


def _normalize_values(payload: dict) -> dict:
    result = {}
    for field, (minimum, maximum) in FIELD_RANGES.items():
        value = payload.get(field)
        try:
            value = int(value) if value is not None else None
        except (TypeError, ValueError):
            value = None
        result[field] = (
            value
            if value is not None and minimum <= value <= maximum
            else None
        )
    if (
        result["systolic"] is not None
        and result["diastolic"] is not None
        and result["systolic"] <= result["diastolic"]
    ):
        result["systolic"] = None
        result["diastolic"] = None
    return result


def _safe_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        error = payload.get("error", payload)
        if isinstance(error, dict):
            code = error.get("code") or response.status_code
            message = error.get("message") or "请求失败"
            return f"{code}: {message}"
    except (ValueError, TypeError):
        pass
    return f"HTTP {response.status_code}"


class DoubaoOcrProvider:
    name = "doubao"

    async def recognize(self, content: bytes, content_type: str) -> dict:
        if not settings.doubao_api_key:
            logger.warning("Doubao OCR unavailable: API Key is not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=DOUBAO_OCR_UNAVAILABLE_MESSAGE,
            )
        if not settings.doubao_endpoint or not settings.doubao_model:
            logger.warning(
                "Doubao OCR unavailable: endpoint or model is not configured"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=DOUBAO_OCR_UNAVAILABLE_MESSAGE,
            )

        headers = {
            "Authorization": f"Bearer {settings.doubao_api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(settings.doubao_timeout, connect=15)
        try:
            jpeg_content = normalize_image_to_jpeg(content, content_type)
            encoded_image = base64.b64encode(jpeg_content).decode("ascii")
            image_data_url = f"data:image/jpeg;base64,{encoded_image}"
            payload = {
                "model": settings.doubao_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_data_url},
                            },
                            {"type": "text", "text": DOUBAO_PROMPT},
                        ],
                    }
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
                "max_tokens": 300,
            }
            async with httpx.AsyncClient(
                timeout=timeout,
                trust_env=False,
            ) as client:
                response = await client.post(
                    settings.doubao_endpoint,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                response_payload = response.json()
            try:
                raw_text = response_payload["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise ValueError("豆包响应中缺少 message.content") from exc
            values = _normalize_values(_extract_json_object(str(raw_text)))
        except httpx.HTTPStatusError as exc:
            detail = _safe_error_detail(exc.response)
            logger.warning("Doubao OCR HTTP error: %s", detail)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=DOUBAO_OCR_UNAVAILABLE_MESSAGE,
            ) from exc
        except HTTPException:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.warning(
                "Doubao OCR request failed: %s: %s",
                type(exc).__name__,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=DOUBAO_OCR_UNAVAILABLE_MESSAGE,
            ) from exc

        complete = is_complete(values)
        return {
            **values,
            "raw_text": [str(raw_text)],
            "confidence": 0.94 if complete and values["heart_rate"] else (
                0.82 if complete else 0.45
            ),
            "complete": complete,
            "recognition_method": "doubao_structured_vision",
            "engine": self.name,
            "provider": "doubao",
            "requires_confirmation": True,
            "notice": "豆包 AI 识别结果仅供录入参考，请核对数值后再保存。",
        }
