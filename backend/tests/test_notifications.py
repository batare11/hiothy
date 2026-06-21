from datetime import datetime

from app.models.blood_pressure import BloodPressureRecord
from app.services.notifications import build_pressure_alert


def record(systolic: int, diastolic: int) -> BloodPressureRecord:
    return BloodPressureRecord(
        systolic=systolic,
        diastolic=diastolic,
        heart_rate=70,
        hypertension_grade=0,
        created_at=datetime.now(),
    )


def test_normal_and_high_normal_do_not_create_alerts():
    assert build_pressure_alert(record(118, 76)) is None
    assert build_pressure_alert(record(135, 85)) is None


def test_grade_alert_severity_increases_with_grade():
    assert build_pressure_alert(record(145, 92)).severity == "warning"
    assert build_pressure_alert(record(165, 102)).severity == "high"
    assert build_pressure_alert(record(185, 112)).severity == "critical"


def test_low_pressure_creates_warning():
    alert = build_pressure_alert(record(85, 55))
    assert alert is not None
    assert alert.message_type == "abnormal_pressure"
    assert alert.severity == "warning"
