from PIL import Image

from app.services.ocr import (
    _field_from_label,
    _select_candidate_values,
    crop_detected_region,
    extract_values,
    infer_values_from_position,
)


def test_extract_values_with_keywords():
    result = extract_values(["SYS 128", "DIA 82", "PUL 72"])
    assert result == {"systolic": 128, "diastolic": 82, "heart_rate": 72}


def test_extract_values_without_keywords():
    result = extract_values(["135", "88", "76"])
    assert result["systolic"] == 135
    assert result["diastolic"] == 88
    assert result["heart_rate"] == 76


def test_extract_values_with_spaced_seven_segment_digits():
    result = extract_values(["SYS 1 2 8", "DIA 8 2", "PUL 7 2"])
    assert result == {"systolic": 128, "diastolic": 82, "heart_rate": 72}


def test_extract_values_with_full_width_digits():
    result = extract_values(["SYS １２８", "DIA ８２", "PUL ７２"])
    assert result == {"systolic": 128, "diastolic": 82, "heart_rate": 72}


def test_extract_values_with_alternative_abbreviations():
    result = extract_values(["SBP 126", "DBP 79", "PR 68 BPM"])
    assert result == {"systolic": 126, "diastolic": 79, "heart_rate": 68}


def test_field_from_chinese_and_english_labels():
    assert _field_from_label("高压") == "systolic"
    assert _field_from_label("DBP") == "diastolic"
    assert _field_from_label("Pulse /min") == "heart_rate"


def test_infer_values_from_vertical_numeric_layout():
    result = [
        [[[100, 10], [250, 10], [250, 80], [100, 80]], "132", 0.99],
        [[[100, 100], [250, 100], [250, 170], [100, 170]], "84", 0.99],
        [[[100, 190], [250, 190], [250, 260], [100, 260]], "71", 0.99],
    ]
    assert infer_values_from_position(result) == {
        "systolic": 132,
        "diastolic": 84,
        "heart_rate": 71,
    }


def test_position_inference_rejects_reversed_pressure():
    result = [
        [[[100, 10], [250, 10], [250, 80], [100, 80]], "80", 0.99],
        [[[100, 100], [250, 100], [250, 170], [100, 170]], "120", 0.99],
    ]
    assert infer_values_from_position(result) == {
        "systolic": None,
        "diastolic": None,
        "heart_rate": None,
    }


def test_crop_detected_region_uses_all_text_bounds():
    image = Image.new("RGB", (1000, 800), "white")
    result = [[[[300, 200], [700, 200], [700, 600], [300, 600]], "SYS", 0.9]]
    cropped = crop_detected_region(image, result)
    assert cropped is not None
    assert cropped.width > 800
    assert cropped.height > 800


def test_candidate_selection_prefers_complete_distinct_three_row_values():
    values, method = _select_candidate_values(
        [
            (
                {"systolic": 125, "diastolic": 69, "heart_rate": 69},
                "text+three_row_display",
            ),
            (
                {"systolic": 125, "diastolic": 81, "heart_rate": 69},
                "three_row_display",
            ),
        ]
    )
    assert values == {"systolic": 125, "diastolic": 81, "heart_rate": 69}
    assert method == "three_row_display"


def test_candidate_selection_rejects_implausibly_narrow_pulse_pressure():
    values, _ = _select_candidate_values(
        [
            ({"systolic": 98, "diastolic": 96, "heart_rate": 88}, "text"),
            (
                {"systolic": 154, "diastolic": 96, "heart_rate": 88},
                "three_row_display",
            ),
        ]
    )
    assert values == {"systolic": 154, "diastolic": 96, "heart_rate": 88}
