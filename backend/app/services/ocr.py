"""血压计图片 OCR 与数值提取服务。"""

import io
import re
from functools import lru_cache

from PIL import Image, ImageEnhance, ImageOps


@lru_cache
def get_ocr_engine():
    """延迟加载 OCR 模型，避免应用启动时阻塞。"""
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def preprocess_image(content: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(content)).convert("RGB")
    image.thumbnail((1800, 1800))
    gray = ImageOps.grayscale(image)
    gray = ImageEnhance.Contrast(gray).enhance(1.8)
    return gray


def extract_values(texts: list[str]) -> dict[str, int | None]:
    """结合关键词与数值范围提取高压、低压、心率。"""
    joined = " ".join(texts).upper()
    values = [int(item) for item in re.findall(r"(?<!\d)\d{2,3}(?!\d)", joined)]

    def keyword_value(pattern: str) -> int | None:
        match = re.search(pattern + r"[^0-9]{0,10}(\d{2,3})", joined)
        return int(match.group(1)) if match else None

    systolic = keyword_value(r"(?:SYS|收缩压|高压)")
    diastolic = keyword_value(r"(?:DIA|舒张压|低压)")
    heart_rate = keyword_value(r"(?:PUL|PULSE|心率|脉搏)")

    pressure_values = [value for value in values if 50 <= value <= 260]
    if (
        systolic is None
        and diastolic is None
        and len(values) >= 2
        and values[0] > values[1]
    ):
        systolic = values[0]
        diastolic = values[1]
        if heart_rate is None and len(values) >= 3:
            heart_rate = values[2]
    if systolic is None and pressure_values:
        systolic = max(pressure_values)
    if diastolic is None and pressure_values:
        candidates = [
            value
            for value in pressure_values
            if value != systolic and 30 <= value <= 180
        ]
        if candidates:
            diastolic = min(candidates)
    if heart_rate is None:
        candidates = [
            value
            for value in values
            if 30 <= value <= 220 and value not in {systolic, diastolic}
        ]
        if candidates:
            heart_rate = candidates[-1]

    return {
        "systolic": systolic,
        "diastolic": diastolic,
        "heart_rate": heart_rate,
    }


def recognize_blood_pressure(content: bytes) -> dict:
    image = preprocess_image(content)
    engine = get_ocr_engine()
    result, _ = engine(image)
    texts = [str(line[1]) for line in (result or []) if len(line) >= 2]
    values = extract_values(texts)
    complete = bool(values["systolic"] and values["diastolic"])
    return {
        **values,
        "raw_text": texts,
        "confidence": 0.85 if complete else 0.45,
        "complete": complete,
        "notice": "OCR 结果仅供录入参考，请核对血压计屏幕数值后再保存。",
    }
