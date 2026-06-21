"""OCR 提供方公共协议与结果工具。"""

from typing import Protocol

OCR_FIELDS = ("systolic", "diastolic", "heart_rate")


class OcrProvider(Protocol):
    name: str

    async def recognize(self, content: bytes, content_type: str) -> dict:
        ...


def is_complete(result: dict) -> bool:
    systolic = result.get("systolic")
    diastolic = result.get("diastolic")
    return bool(systolic and diastolic and systolic > diastolic)


def field_count(result: dict) -> int:
    return sum(result.get(field) is not None for field in OCR_FIELDS)


def result_rank(result: dict) -> tuple[int, int, float]:
    return (
        int(is_complete(result)),
        field_count(result),
        float(result.get("confidence") or 0),
    )
