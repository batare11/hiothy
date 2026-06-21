"""现有 RapidOCR 血压专用识别适配器。"""

import asyncio

from app.services.ocr import recognize_blood_pressure


class RapidOcrProvider:
    name = "rapid"

    async def recognize(self, content: bytes, content_type: str) -> dict:
        result = await asyncio.to_thread(recognize_blood_pressure, content)
        return {
            **result,
            "engine": self.name,
            "provider": "rapidocr",
        }
