import asyncio
import base64
import io

import httpx
import pytest
from fastapi import HTTPException
from PIL import Image

from app.core.config import settings
from app.services.ocr_providers.doubao import (
    DOUBAO_OCR_UNAVAILABLE_MESSAGE,
    DoubaoOcrProvider,
    _extract_json_object,
    _normalize_values,
)


def image_bytes(image_format: str = "PNG") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (8, 8), color="white").save(output, format=image_format)
    return output.getvalue()


def test_doubao_json_parser_and_validation():
    payload = _extract_json_object(
        '```json\n{"systolic":128,"diastolic":82,"heart_rate":72}\n```'
    )
    assert _normalize_values(payload) == {
        "systolic": 128,
        "diastolic": 82,
        "heart_rate": 72,
    }


def test_doubao_rejects_out_of_range_and_reversed_pressure():
    assert _normalize_values(
        {"systolic": 300, "diastolic": 20, "heart_rate": 500}
    ) == {"systolic": None, "diastolic": None, "heart_rate": None}
    assert _normalize_values(
        {"systolic": 80, "diastolic": 120, "heart_rate": 70}
    ) == {"systolic": None, "diastolic": None, "heart_rate": 70}


def test_doubao_requires_configuration(monkeypatch):
    monkeypatch.setattr(settings, "doubao_api_key", "")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            DoubaoOcrProvider().recognize(image_bytes(), "image/png")
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == DOUBAO_OCR_UNAVAILABLE_MESSAGE


def test_doubao_sends_base64_jpeg_and_returns_structured_values(monkeypatch):
    monkeypatch.setattr(settings, "doubao_api_key", "test-key")
    monkeypatch.setattr(
        settings,
        "doubao_endpoint",
        "https://ark.test/api/v3/chat/completions",
    )
    monkeypatch.setattr(settings, "doubao_model", "ep-test-endpoint")
    captured = {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"systolic":128,'
                                    '"diastolic":82,'
                                    '"heart_rate":72}'
                                )
                            }
                        }
                    ]
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    result = asyncio.run(
        DoubaoOcrProvider().recognize(image_bytes("WEBP"), "image/webp")
    )

    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["payload"]["model"] == "ep-test-endpoint"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    image_url = captured["payload"]["messages"][0]["content"][0][
        "image_url"
    ]["url"]
    assert image_url.startswith("data:image/jpeg;base64,")
    assert base64.b64decode(image_url.split(",", 1)[1]).startswith(
        b"\xff\xd8\xff"
    )
    assert result["provider"] == "doubao"
    assert result["complete"] is True
    assert result["systolic"] == 128


def test_doubao_http_error_is_safely_wrapped(monkeypatch):
    monkeypatch.setattr(settings, "doubao_api_key", "test-key")
    monkeypatch.setattr(
        settings,
        "doubao_endpoint",
        "https://ark.test/api/v3/chat/completions",
    )
    monkeypatch.setattr(settings, "doubao_model", "ep-test-endpoint")

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, headers, json):
            return httpx.Response(
                429,
                request=httpx.Request("POST", url),
                json={"error": {"code": "LimitExceeded", "message": "quota"}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            DoubaoOcrProvider().recognize(image_bytes(), "image/png")
        )
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == DOUBAO_OCR_UNAVAILABLE_MESSAGE
