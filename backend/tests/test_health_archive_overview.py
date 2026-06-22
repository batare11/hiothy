from datetime import datetime
from types import SimpleNamespace

from app.api.routes.blood_pressure import (
    calculate_overview_stats,
    calculate_period_stats,
)


def make_record(day: int, hour: int, systolic: int, diastolic: int):
    return SimpleNamespace(
        created_at=datetime(2026, 6, day, hour, 0),
        systolic=systolic,
        diastolic=diastolic,
    )


def test_overview_stats_count_distinct_days_and_rates():
    records = [
        make_record(20, 8, 118, 78),
        make_record(20, 20, 130, 85),
        make_record(21, 9, 145, 95),
    ]

    stats = calculate_overview_stats(records)

    assert stats == {
        "total": 3,
        "record_days": 2,
        "normal_count": 1,
        "abnormal_count": 2,
        "normal_rate": 33.3,
        "abnormal_rate": 66.7,
    }


def test_overview_stats_are_zero_without_records():
    assert calculate_overview_stats([]) == {
        "total": 0,
        "record_days": 0,
        "normal_count": 0,
        "abnormal_count": 0,
        "normal_rate": 0,
        "abnormal_rate": 0,
    }


def test_period_stats_include_averages_and_rates():
    records = [
        SimpleNamespace(
            created_at=datetime(2026, 6, 20, 8, 0),
            systolic=118,
            diastolic=78,
            heart_rate=70,
        ),
        SimpleNamespace(
            created_at=datetime(2026, 6, 21, 8, 0),
            systolic=142,
            diastolic=92,
            heart_rate=80,
        ),
    ]

    assert calculate_period_stats(records) == {
        "total": 2,
        "normal_count": 1,
        "abnormal_count": 1,
        "normal_rate": 50.0,
        "abnormal_rate": 50.0,
        "avg_systolic": 130.0,
        "avg_diastolic": 85.0,
        "avg_heart_rate": 75.0,
    }
