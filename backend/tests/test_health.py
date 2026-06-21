from app.services.health import classify_pressure_detail


def test_pressure_classification_boundaries():
    cases = [
        ((119, 79), ("normal", 0)),
        ((120, 80), ("high_normal", 0)),
        ((139, 89), ("high_normal", 0)),
        ((140, 90), ("grade_1", 1)),
        ((159, 99), ("grade_1", 1)),
        ((160, 100), ("grade_2", 2)),
        ((179, 109), ("grade_2", 2)),
        ((180, 110), ("grade_3", 3)),
        ((85, 55), ("low", 0)),
    ]
    for (systolic, diastolic), expected in cases:
        result = classify_pressure_detail(systolic, diastolic)
        assert (result["category"], result["hypertension_grade"]) == expected


def test_pressure_classification_uses_higher_grade():
    result = classify_pressure_detail(150, 105)
    assert result["category"] == "grade_2"
    assert result["hypertension_grade"] == 2


def test_isolated_systolic_hypertension_is_labeled():
    result = classify_pressure_detail(145, 85)
    assert result["category"] == "grade_1"
    assert "单纯收缩期" in result["status_text"]

    severe_result = classify_pressure_detail(185, 85)
    assert severe_result["category"] == "grade_3"
    assert "单纯收缩期" in severe_result["status_text"]
