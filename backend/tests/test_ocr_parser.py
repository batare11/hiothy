from app.services.ocr import extract_values


def test_extract_values_with_keywords():
    result = extract_values(["SYS 128", "DIA 82", "PUL 72"])
    assert result == {"systolic": 128, "diastolic": 82, "heart_rate": 72}


def test_extract_values_without_keywords():
    result = extract_values(["135", "88", "76"])
    assert result["systolic"] == 135
    assert result["diastolic"] == 88
    assert result["heart_rate"] == 76
