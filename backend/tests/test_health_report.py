import asyncio
from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import settings
from app.services.health_report import (
    AI_REPORT_UNAVAILABLE_MESSAGE,
    DEEPSEEK_HEALTH_MODEL,
    build_health_report_payload,
    generate_health_report,
)


def test_health_report_payload_contains_profile_records_and_notes():
    archive = SimpleNamespace(
        age=60,
        gender=1,
        marital_status=1,
        height_cm=170,
        weight_jin=140,
        smoking=False,
        drinking=True,
        staying_up_late=True,
        note="长期服药",
    )
    records = [
        SimpleNamespace(
            created_at=datetime(2026, 6, 21, 20, 15),
            systolic=138,
            diastolic=88,
            heart_rate=75,
            note="服药后测量",
        ),
        SimpleNamespace(
            created_at=datetime(2026, 6, 22, 8, 30),
            systolic=145,
            diastolic=92,
            heart_rate=78,
            note="昨晚熬夜",
        )
    ]

    payload = build_health_report_payload(archive, records)

    assert payload["profile"]["age"] == 60
    assert payload["profile"]["bmi"] == 24.2
    assert payload["profile"]["bmi_category"] == "超重"
    assert payload["profile"]["gender_text"] == "男"
    assert payload["profile"]["smoking_text"] == "不吸烟"
    assert payload["profile"]["drinking_text"] == "饮酒"
    assert payload["profile"]["staying_up_late_text"] == "经常熬夜"
    assert payload["data_scope"]["record_count"] == 2
    assert payload["data_scope"]["record_days"] == 2
    assert payload["data_scope"]["first_measurement_at"] == (
        "2026-06-21T20:15:00"
    )
    assert payload["data_scope"]["last_measurement_at"] == (
        "2026-06-22T08:30:00"
    )
    assert len(payload["blood_pressure_records"]) == 2
    assert payload["blood_pressure_records"][0]["note"] == "服药后测量"
    assert payload["blood_pressure_records"][1]["note"] == "昨晚熬夜"
    assert payload["blood_pressure_records"][1]["classification"] == "高血压1级"


def test_health_report_uses_only_deepseek_v4_pro(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        settings,
        "deepseek_endpoint",
        "https://api.deepseek.com/chat/completions",
    )
    captured = {}

    class FakeResponse:
        status_code = 200
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": "【健康概览】\n测试报告"}}
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url, headers, json):
            captured.update({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: FakeClient())
    archive = SimpleNamespace(
        age=None,
        gender=None,
        marital_status=None,
        height_cm=None,
        weight_jin=None,
        smoking=False,
        drinking=False,
        staying_up_late=False,
        note=None,
    )

    report = asyncio.run(generate_health_report(archive, []))

    assert report.startswith("【健康概览】")
    assert captured["json"]["model"] == DEEPSEEK_HEALTH_MODEL
    assert captured["json"]["model"] == "deepseek-v4-pro"


def test_health_report_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "")
    archive = SimpleNamespace(
        age=None,
        gender=None,
        marital_status=None,
        height_cm=None,
        weight_jin=None,
        smoking=False,
        drinking=False,
        staying_up_late=False,
        note=None,
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(generate_health_report(archive, []))

    assert exc_info.value.detail == AI_REPORT_UNAVAILABLE_MESSAGE
