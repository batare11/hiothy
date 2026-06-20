"""血压计图片 OCR 与数值提取服务。"""

import io
import re
from functools import lru_cache
from typing import Any

from PIL import Image, ImageEnhance, ImageOps

FIELD_RANGES = {
    "systolic": (50, 260),
    "diastolic": (30, 180),
    "heart_rate": (30, 220),
}
EMPTY_VALUES = {"systolic": None, "diastolic": None, "heart_rate": None}


@lru_cache
def get_ocr_engine():
    """延迟加载 OCR 模型，避免应用启动时阻塞。"""
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def preprocess_images(content: bytes) -> list[Image.Image]:
    image = ImageOps.exif_transpose(
        Image.open(io.BytesIO(content))
    ).convert("RGB")
    image.thumbnail((1800, 1800))
    gray = ImageOps.grayscale(image)
    enhanced = ImageEnhance.Contrast(gray).enhance(1.8)
    autocontrast = ImageOps.autocontrast(gray, cutoff=1)
    # 数码管在反光、低对比度场景下对预处理非常敏感。保留原图并增加两种
    # 灰度版本，稍后选择提取数值最完整的一次结果。
    return [image, enhanced, autocontrast]


def _field_from_label(text: str) -> str | None:
    """兼容英文缩写、中文标签和常见心率单位。"""
    normalized = re.sub(r"[\s:：_\-/]", "", str(text).upper())
    aliases = {
        "systolic": ("SYS", "SBP", "收缩压", "高压"),
        "diastolic": ("DIA", "DBP", "舒张压", "低压"),
        "heart_rate": ("PUL", "PULSE", "PR", "BPM", "心率", "脉搏"),
    }
    for field, field_aliases in aliases.items():
        if any(alias in normalized for alias in field_aliases):
            return field
    return None


def _valid_value(field: str, value: int | None) -> bool:
    if value is None:
        return False
    low, high = FIELD_RANGES[field]
    return low <= value <= high


def _merge_values(
    base: dict[str, int | None],
    extra: dict[str, int | None],
) -> dict[str, int | None]:
    merged = dict(base)
    for field, value in extra.items():
        if merged.get(field) is None and _valid_value(field, value):
            merged[field] = value
    return merged


def _box_bounds(box: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    return min(xs), min(ys), max(xs), max(ys)


def crop_detected_region(
    image: Image.Image,
    ocr_result: list,
) -> Image.Image | None:
    """裁剪首轮 OCR 检出的屏幕区域并放大，提升七段数码识别率。"""
    bounds = [
        _box_bounds(line[0])
        for line in (ocr_result or [])
        if len(line) >= 2 and line[0]
    ]
    if not bounds:
        return None

    margin_x = image.width * 0.05
    margin_y = image.height * 0.05
    box = (
        max(0, int(min(item[0] for item in bounds) - margin_x)),
        max(0, int(min(item[1] for item in bounds) - margin_y)),
        min(image.width, int(max(item[2] for item in bounds) + margin_x)),
        min(image.height, int(max(item[3] for item in bounds) + margin_y)),
    )
    width = box[2] - box[0]
    height = box[3] - box[1]
    if width < 80 or height < 80:
        return None

    cropped = ImageOps.autocontrast(ImageOps.grayscale(image.crop(box)), cutoff=1)
    scale = min(2.0, 1800 / max(width, height))
    if scale > 1:
        cropped = cropped.resize(
            (int(width * scale), int(height * scale)),
            Image.Resampling.LANCZOS,
        )
    return cropped


def _recognize_crop_number(engine: Any, crop: Image.Image) -> int | None:
    """跳过文本检测，直接识别血压计的一行七段数码。"""
    result, _ = engine(crop, use_det=False, use_cls=False, use_rec=True)
    if not result:
        return None
    digits = re.sub(r"\D", "", str(result[0][0]))
    if not 2 <= len(digits) <= 3:
        return None
    return int(digits)


def recognize_labeled_rows(
    source_image: Image.Image,
    ocr_result: list,
    engine: Any,
) -> dict[str, int | None]:
    """按 SYS、DIA、PUL 标签定位并分别识别三行数字。"""
    labels: dict[str, tuple[float, float, float, float]] = {}
    for line in ocr_result or []:
        if len(line) < 2:
            continue
        field = _field_from_label(str(line[1]))
        if field:
            labels[field] = _box_bounds(line[0])

    if len(labels) < 2:
        return dict(EMPTY_VALUES)

    ordered_fields = sorted(
        labels,
        key=lambda field: (labels[field][1] + labels[field][3]) / 2,
    )
    centers = [
        (labels[field][1] + labels[field][3]) / 2
        for field in ordered_fields
    ]
    spacings = [
        centers[index + 1] - centers[index]
        for index in range(len(centers) - 1)
        if centers[index + 1] > centers[index]
    ]
    row_height = (
        sum(spacings) / len(spacings)
        if spacings
        else source_image.height / 4
    )
    label_right = max(bounds[2] for bounds in labels.values())
    x_start = max(0, int(label_right + row_height * 0.12))

    numeric_right = 0.0
    for line in ocr_result or []:
        if len(line) < 2:
            continue
        left, top, right, bottom = _box_bounds(line[0])
        if left >= label_right and bottom - top >= row_height * 0.45:
            numeric_right = max(numeric_right, right)
    x_end = min(
        source_image.width,
        int(numeric_right + row_height * 0.12)
        if numeric_right
        else int(source_image.width * 0.95),
    )

    values = dict(EMPTY_VALUES)
    for index, field in enumerate(ordered_fields):
        center_y = centers[index]
        if index == 0:
            y_start = center_y - row_height * 0.75
        else:
            y_start = (centers[index - 1] + center_y) / 2 + row_height * 0.12

        if index == len(centers) - 1:
            y_end = center_y + row_height * 0.75
        else:
            y_end = (center_y + centers[index + 1]) / 2 + row_height * 0.12

        y_start = max(0, int(y_start))
        y_end = min(source_image.height, int(y_end))
        if x_end <= x_start or y_end <= y_start:
            continue
        value = _recognize_crop_number(
            engine,
            source_image.crop((x_start, y_start, x_end, y_end)),
        )
        if _valid_value(field, value):
            values[field] = value
    return values


def infer_values_from_position(ocr_result: list) -> dict[str, int | None]:
    """无标签或标签识别失败时，根据数字从上到下的布局推断三项指标。"""
    numeric_items = []
    for line in ocr_result or []:
        if len(line) < 2:
            continue
        digits = re.sub(r"\D", "", str(line[1]))
        if not 2 <= len(digits) <= 3:
            continue
        value = int(digits)
        if not 30 <= value <= 260:
            continue
        left, top, right, bottom = _box_bounds(line[0])
        numeric_items.append(
            {
                "value": value,
                "center_y": (top + bottom) / 2,
                "area": (right - left) * (bottom - top),
            }
        )

    # 日期、时间和存储编号通常更小，优先选择面积较大的主显示数字。
    if len(numeric_items) > 3:
        numeric_items = sorted(
            numeric_items,
            key=lambda item: item["area"],
            reverse=True,
        )[:3]
    numeric_items.sort(key=lambda item: item["center_y"])
    values = [item["value"] for item in numeric_items]
    if len(values) < 2 or values[0] <= values[1]:
        return dict(EMPTY_VALUES)
    return {
        "systolic": values[0] if _valid_value("systolic", values[0]) else None,
        "diastolic": values[1] if _valid_value("diastolic", values[1]) else None,
        "heart_rate": (
            values[2]
            if len(values) >= 3 and _valid_value("heart_rate", values[2])
            else None
        ),
    }


def recognize_three_row_display(
    source_image: Image.Image,
    ocr_result: list,
    engine: Any,
) -> dict[str, int | None]:
    """识别没有可用标签、但采用高压/低压/心率三行布局的显示屏。"""
    bounds = []
    for line in ocr_result or []:
        if len(line) < 2 or not line[0]:
            continue
        left, top, right, bottom = _box_bounds(line[0])
        text = str(line[1])
        if re.search(r"\d", text) or bottom - top > source_image.height * 0.18:
            bounds.append((left, top, right, bottom))
    if not bounds:
        return dict(EMPTY_VALUES)

    left = max(0, int(min(item[0] for item in bounds) - source_image.width * 0.02))
    top = max(0, int(min(item[1] for item in bounds) - source_image.height * 0.02))
    right = min(
        source_image.width,
        int(max(item[2] for item in bounds) + source_image.width * 0.02),
    )
    bottom = min(
        source_image.height,
        int(max(item[3] for item in bounds) + source_image.height * 0.02),
    )
    width, height = right - left, bottom - top
    if width < 60 or height < 120:
        return dict(EMPTY_VALUES)

    fields = ("systolic", "diastolic", "heart_rate")
    values = dict(EMPTY_VALUES)
    for index, field in enumerate(fields):
        row_top = top + int(height * index / 3)
        row_bottom = top + int(height * (index + 1) / 3)
        padding = int(height * 0.025)
        crop = source_image.crop(
            (
                left,
                max(top, row_top - padding),
                right,
                min(bottom, row_bottom + padding),
            )
        )
        value = _recognize_crop_number(engine, crop)
        if _valid_value(field, value):
            values[field] = value

    if values["systolic"] and values["diastolic"]:
        if values["systolic"] <= values["diastolic"]:
            return dict(EMPTY_VALUES)
    return values


def extract_values(texts: list[str]) -> dict[str, int | None]:
    """结合关键词与数值范围提取高压、低压、心率。"""
    normalized_texts = []
    digit_translation = str.maketrans("０１２３４５６７８９", "0123456789")
    for text in texts:
        normalized = str(text).translate(digit_translation).upper()
        # 部分 OCR 会把同一行七段数码识别成 “1 2 8”。
        normalized = re.sub(r"(?<=\d)\s+(?=\d)", "", normalized)
        normalized_texts.append(normalized)

    joined = " ".join(normalized_texts)
    values = [int(item) for item in re.findall(r"(?<!\d)\d{2,3}(?!\d)", joined)]

    def keyword_value(pattern: str) -> int | None:
        match = re.search(pattern + r"[^0-9]{0,20}(\d{2,3})", joined)
        return int(match.group(1)) if match else None

    systolic = keyword_value(r"(?:SYS|SBP|收缩压|高压)")
    diastolic = keyword_value(r"(?:DIA|DBP|舒张压|低压)")
    heart_rate = keyword_value(r"(?:PUL|PULSE|PR|BPM|心率|脉搏)")

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


def _candidate_score(values: dict[str, int | None]) -> tuple[int, int]:
    complete = bool(
        values["systolic"]
        and values["diastolic"]
        and values["systolic"] > values["diastolic"]
    )
    count = sum(value is not None for value in values.values())
    return int(complete), count


def _recognize_image_candidate(
    image: Image.Image,
    engine: Any,
) -> tuple[dict[str, int | None], list[str], str]:
    result, _ = engine(image)
    texts = [str(line[1]) for line in (result or []) if len(line) >= 2]
    values = extract_values(texts)
    method = "text"

    labeled = recognize_labeled_rows(image, result or [], engine)
    if _candidate_score(labeled) > _candidate_score(values):
        method = "labeled_rows"
    values = _merge_values(values, labeled)

    positioned = infer_values_from_position(result or [])
    if _candidate_score(positioned) > _candidate_score(values):
        method = "position"
    values = _merge_values(values, positioned)

    if _candidate_score(values) != (1, 3):
        three_rows = recognize_three_row_display(image, result or [], engine)
        if _candidate_score(three_rows) > _candidate_score(values):
            method = "three_row_display"
        values = _merge_values(values, three_rows)
    return values, texts, method


def recognize_blood_pressure(content: bytes) -> dict:
    engine = get_ocr_engine()
    candidates = []
    images = preprocess_images(content)
    for index, image in enumerate(images):
        values, texts, method = _recognize_image_candidate(image, engine)
        candidates.append((values, texts, method))
        if _candidate_score(values) == (1, 3):
            break
        if index == 0:
            result, _ = engine(image)
            cropped = crop_detected_region(image, result or [])
            if cropped is not None:
                images.insert(1, cropped)

    # 照片方向不正确时，补充两个常见旋转方向；仅在常规策略失败后执行。
    if max(_candidate_score(item[0]) for item in candidates) != (1, 3):
        source = images[0]
        for angle in (90, 270):
            rotated = source.rotate(angle, expand=True)
            values, texts, method = _recognize_image_candidate(rotated, engine)
            candidates.append((values, texts, f"rotated_{angle}_{method}"))
            if _candidate_score(values) == (1, 3):
                break

    values, texts, method = max(
        candidates,
        key=lambda item: _candidate_score(item[0]),
    )
    complete = _candidate_score(values)[0] == 1
    all_fields_complete = complete and values["heart_rate"] is not None
    return {
        **values,
        "raw_text": texts,
        "confidence": 0.92 if all_fields_complete else (0.80 if complete else 0.40),
        "complete": complete,
        "recognition_method": method,
        "requires_confirmation": True,
        "notice": "OCR 结果仅供录入参考，请核对血压计屏幕数值后再保存。",
    }
