"""OCR 提供方注册、选择和自动回退策略。"""

import logging

from fastapi import HTTPException

from app.core.config import settings
from app.services.ocr_providers.base import is_complete, result_rank
from app.services.ocr_providers.glm import (
    GLM_OCR_UNAVAILABLE_MESSAGE,
    GlmOcrProvider,
)
from app.services.ocr_providers.rapid import RapidOcrProvider

logger = logging.getLogger(__name__)

PROVIDERS = {
    "rapid": RapidOcrProvider(),
    "glm": GlmOcrProvider(),
}
SUPPORTED_ENGINES = ("rapid", "glm", "auto")


def _rapid_is_confident(result: dict) -> bool:
    return bool(
        is_complete(result)
        and result.get("heart_rate") is not None
        and float(result.get("confidence") or 0) >= settings.ocr_auto_min_confidence
    )


async def recognize_with_provider(
    content: bytes,
    content_type: str,
    engine: str,
) -> dict:
    normalized_engine = engine.strip().lower()
    if normalized_engine not in SUPPORTED_ENGINES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的识别引擎：{engine}",
        )
    if normalized_engine != "auto":
        return await PROVIDERS[normalized_engine].recognize(content, content_type)

    rapid_result = await PROVIDERS["rapid"].recognize(content, content_type)
    if _rapid_is_confident(rapid_result):
        return {
            **rapid_result,
            "engine": "auto",
            "provider": "rapidocr",
            "fallback_used": False,
        }

    try:
        glm_result = await PROVIDERS["glm"].recognize(content, content_type)
    except HTTPException as exc:
        logger.warning("Auto OCR fallback unavailable: %s", exc.detail)
        return {
            **rapid_result,
            "engine": "auto",
            "provider": "rapidocr",
            "fallback_used": False,
            "notice": (
                f"{rapid_result.get('notice', '')}"
                f" {GLM_OCR_UNAVAILABLE_MESSAGE}，已返回快速识别结果。"
            ).strip(),
        }

    best_result = max((rapid_result, glm_result), key=result_rank)
    selected_provider = best_result.get("provider")
    return {
        **best_result,
        "engine": "auto",
        "provider": selected_provider,
        "fallback_used": True,
        "candidate_providers": ["rapidocr", "glm"],
    }
