"""可插拔 OCR 提供方。"""

from app.services.ocr_providers.registry import recognize_with_provider

__all__ = ["recognize_with_provider"]
