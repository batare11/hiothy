from datetime import datetime
from types import SimpleNamespace

from app.api.routes.blood_pressure import build_single_day_trend_points


def make_record(
    hour: int,
    minute: int,
    systolic: int,
    diastolic: int,
    heart_rate: int | None,
):
    return SimpleNamespace(
        created_at=datetime(2026, 6, 22, hour, minute),
        systolic=systolic,
        diastolic=diastolic,
        heart_rate=heart_rate,
    )


def test_build_single_day_trend_points_keeps_actual_measurement_times():
    records = [
        make_record(8, 10, 120, 80, 70),
        make_record(9, 45, 130, 84, 74),
        make_record(22, 5, 118, 78, None),
    ]

    points = build_single_day_trend_points(records)

    assert points == [
        {
            "label": "08:10",
            "systolic": 120.0,
            "diastolic": 80.0,
            "heart_rate": 70.0,
            "count": 1,
        },
        {
            "label": "09:45",
            "systolic": 130.0,
            "diastolic": 84.0,
            "heart_rate": 74.0,
            "count": 1,
        },
        {
            "label": "22:05",
            "systolic": 118.0,
            "diastolic": 78.0,
            "heart_rate": None,
            "count": 1,
        },
    ]
