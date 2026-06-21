import asyncio
import base64
import io
import time

import pytest
from fastapi import HTTPException
from PIL import Image

from app.core.config import settings
from app.main import app
from app.services.ocr_providers import registry
from app.services.ocr_providers.glm import (
    GLM_OCR_UNAVAILABLE_MESSAGE,
    GlmOcrProvider,
    _extract_ocr_text,
    _parse_json_content,
    _resolve_endpoint,
    _safe_error_detail,
)
from app.services.ocr_providers.temp_files import (
    create_temp_image,
    delete_temp_image,
    resolve_temp_image,
)


class FakeProvider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    async def recognize(self, content: bytes, content_type: str) -> dict:
        self.calls += 1
        if self.error:
            raise self.error
        return dict(self.result)


def image_bytes(image_format: str = "PNG") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (8, 8), color="white").save(output, format=image_format)
    return output.getvalue()


def test_parse_glm_structured_json():
    result = _parse_json_content(
        '```json\n{"systolic":128,"diastolic":82,"heart_rate":72}\n```'
    )
    assert result == {"systolic": 128, "diastolic": 82, "heart_rate": 72}


def test_parse_glm_alias_fields():
    result = _parse_json_content('{"sys":"135","dia":"88","pulse":"76"}')
    assert result == {"systolic": 135, "diastolic": 88, "heart_rate": 76}


def test_glm_ocr_endpoint_and_response_protocol():
    assert _resolve_endpoint(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    ) == "https://open.bigmodel.cn/api/paas/v4/layout_parsing"
    assert _resolve_endpoint(
        "https://open.bigmodel.cn/api/paas/v4/layout_parsing"
    ) == "https://open.bigmodel.cn/api/paas/v4/layout_parsing"
    text = _extract_ocr_text(
        {
            "md_results": "SYS 128\nDIA 82\nPUL 72",
            "layout_details": [],
        }
    )
    assert "SYS 128" in text


def test_glm_error_detail_is_safe_and_useful():
    import httpx

    response = httpx.Response(
        400,
        json={"error": {"code": "1214", "message": "invalid image"}},
    )
    assert _safe_error_detail(response) == "1214: invalid image"


def test_temporary_image_route_supports_get_and_head():
    route = next(
        item
        for item in app.routes
        if item.path == "/api/v1/ocr/temp/{filename}"
    )
    assert {"GET", "HEAD"}.issubset(route.methods)


def test_temporary_image_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ocr_temp_dir", str(tmp_path))
    monkeypatch.setattr(settings, "ocr_temp_file_ttl", 300)
    filename, path = create_temp_image(image_bytes("PNG"), "image/png")
    assert filename.endswith(".jpg")
    assert resolve_temp_image(filename) == path
    with Image.open(path) as image:
        assert image.format == "JPEG"
    delete_temp_image(path)
    assert resolve_temp_image(filename) is None


def test_webp_is_normalized_to_glm_supported_jpeg(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ocr_temp_dir", str(tmp_path))
    filename, path = create_temp_image(image_bytes("WEBP"), "image/webp")
    assert filename.endswith(".jpg")
    with Image.open(path) as image:
        assert image.format == "JPEG"


def test_expired_temporary_image_is_removed(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ocr_temp_dir", str(tmp_path))
    monkeypatch.setattr(settings, "ocr_temp_file_ttl", 60)
    filename, path = create_temp_image(image_bytes("PNG"), "image/png")
    old_time = time.time() - 120
    path.touch()
    import os

    os.utime(path, (old_time, old_time))
    assert resolve_temp_image(filename) is None
    assert not path.exists()


def test_auto_uses_rapid_when_confident(monkeypatch):
    rapid = FakeProvider(
        {
            "systolic": 128,
            "diastolic": 82,
            "heart_rate": 72,
            "complete": True,
            "confidence": 0.92,
            "provider": "rapidocr",
        }
    )
    glm = FakeProvider({})
    monkeypatch.setitem(registry.PROVIDERS, "rapid", rapid)
    monkeypatch.setitem(registry.PROVIDERS, "glm", glm)
    monkeypatch.setattr(settings, "ocr_auto_min_confidence", 0.85)

    result = asyncio.run(
        registry.recognize_with_provider(b"image", "image/png", "auto")
    )
    assert result["provider"] == "rapidocr"
    assert result["fallback_used"] is False
    assert rapid.calls == 1
    assert glm.calls == 0


def test_auto_uses_glm_when_rapid_is_incomplete(monkeypatch):
    rapid = FakeProvider(
        {
            "systolic": 128,
            "diastolic": None,
            "heart_rate": None,
            "complete": False,
            "confidence": 0.4,
            "provider": "rapidocr",
        }
    )
    glm = FakeProvider(
        {
            "systolic": 128,
            "diastolic": 82,
            "heart_rate": 72,
            "complete": True,
            "confidence": 0.9,
            "provider": "glm",
        }
    )
    monkeypatch.setitem(registry.PROVIDERS, "rapid", rapid)
    monkeypatch.setitem(registry.PROVIDERS, "glm", glm)

    result = asyncio.run(
        registry.recognize_with_provider(b"image", "image/png", "auto")
    )
    assert result["provider"] == "glm"
    assert result["fallback_used"] is True
    assert rapid.calls == 1
    assert glm.calls == 1


def test_auto_returns_rapid_when_glm_is_unavailable(monkeypatch):
    rapid = FakeProvider(
        {
            "systolic": 128,
            "diastolic": None,
            "heart_rate": None,
            "complete": False,
            "confidence": 0.4,
            "provider": "rapidocr",
            "notice": "请核对。",
        }
    )
    glm = FakeProvider(
        error=HTTPException(status_code=503, detail="GLM 未配置")
    )
    monkeypatch.setitem(registry.PROVIDERS, "rapid", rapid)
    monkeypatch.setitem(registry.PROVIDERS, "glm", glm)

    result = asyncio.run(
        registry.recognize_with_provider(b"image", "image/png", "auto")
    )
    assert result["provider"] == "rapidocr"
    assert GLM_OCR_UNAVAILABLE_MESSAGE in result["notice"]


def test_glm_missing_configuration_uses_unified_message(monkeypatch):
    monkeypatch.setattr(settings, "glm_ocr_api_key", "")
    provider = GlmOcrProvider()

    try:
        asyncio.run(provider.recognize(image_bytes(), "image/png"))
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == GLM_OCR_UNAVAILABLE_MESSAGE
    else:
        raise AssertionError("GLM 配置缺失时应抛出 HTTPException")


def test_glm_sends_normalized_jpeg_as_base64_data_url(monkeypatch):
    import httpx

    monkeypatch.setattr(settings, "glm_ocr_api_key", "test-key")
    monkeypatch.setattr(
        settings,
        "glm_ocr_endpoint",
        "https://glm.test/api/paas/v4/chat/completions",
    )
    monkeypatch.setattr(settings, "glm_ocr_model", "glm-ocr")
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
            captured["payload"] = json
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "md_results": "SYS 128\nDIA 82\nPUL 72",
                    "layout_details": [
                        [
                        {
                            "label": "text",
                            "content": "SYS 128 DIA 82 PUL 72",
                        }
                        ]
                    ],
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    result = asyncio.run(
        GlmOcrProvider().recognize(image_bytes("WEBP"), "image/webp")
    )

    assert captured["url"].endswith("/layout_parsing")
    assert set(captured["payload"]) == {
        "model",
        "file",
        "return_crop_images",
        "need_layout_visualization",
    }
    image_url = captured["payload"]["file"]
    assert image_url.startswith("data:image/jpeg;base64,")
    encoded = image_url.split(",", 1)[1]
    decoded = base64.b64decode(encoded)
    assert decoded.startswith(b"\xff\xd8\xff")
    assert result["systolic"] == 128
    assert result["complete"] is True


@pytest.mark.parametrize("response_status", [402, 429, 500])
def test_glm_http_errors_use_unified_message(
    monkeypatch, tmp_path, response_status
):
    import httpx

    monkeypatch.setattr(settings, "glm_ocr_api_key", "test-key")
    monkeypatch.setattr(settings, "glm_ocr_endpoint", "https://glm.test/ocr")
    monkeypatch.setattr(settings, "glm_ocr_model", "glm-ocr")
    monkeypatch.setattr(
        settings,
        "glm_ocr_public_base_url",
        "https://example.test/ocr/temp",
    )
    monkeypatch.setattr(settings, "ocr_temp_dir", str(tmp_path))

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, headers, json):
            request = httpx.Request("POST", url)
            return httpx.Response(
                response_status,
                request=request,
                json={"error": {"code": "quota", "message": "limit reached"}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    provider = GlmOcrProvider()

    try:
        asyncio.run(provider.recognize(image_bytes(), "image/png"))
    except HTTPException as exc:
        assert exc.status_code == 502
        assert exc.detail == GLM_OCR_UNAVAILABLE_MESSAGE
    else:
        raise AssertionError("GLM HTTP 错误时应抛出 HTTPException")
    assert not list(tmp_path.iterdir())


def test_glm_network_errors_use_unified_message(monkeypatch, tmp_path):
    import httpx

    monkeypatch.setattr(settings, "glm_ocr_api_key", "test-key")
    monkeypatch.setattr(settings, "glm_ocr_endpoint", "https://glm.test/ocr")
    monkeypatch.setattr(settings, "glm_ocr_model", "glm-ocr")
    monkeypatch.setattr(
        settings,
        "glm_ocr_public_base_url",
        "https://example.test/ocr/temp",
    )
    monkeypatch.setattr(settings, "ocr_temp_dir", str(tmp_path))

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, headers, json):
            raise httpx.ConnectError(
                "connection failed",
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    provider = GlmOcrProvider()

    try:
        asyncio.run(provider.recognize(image_bytes(), "image/png"))
    except HTTPException as exc:
        assert exc.status_code == 502
        assert exc.detail == GLM_OCR_UNAVAILABLE_MESSAGE
    else:
        raise AssertionError("GLM 网络错误时应抛出 HTTPException")
    assert not list(tmp_path.iterdir())


def test_glm_invalid_response_uses_unified_message(monkeypatch, tmp_path):
    import httpx

    monkeypatch.setattr(settings, "glm_ocr_api_key", "test-key")
    monkeypatch.setattr(settings, "glm_ocr_endpoint", "https://glm.test/ocr")
    monkeypatch.setattr(settings, "glm_ocr_model", "glm-ocr")
    monkeypatch.setattr(
        settings,
        "glm_ocr_public_base_url",
        "https://example.test/ocr/temp",
    )
    monkeypatch.setattr(settings, "ocr_temp_dir", str(tmp_path))

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, headers, json):
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                content=b"not-json",
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    provider = GlmOcrProvider()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(provider.recognize(image_bytes(), "image/png"))
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == GLM_OCR_UNAVAILABLE_MESSAGE
    assert not list(tmp_path.iterdir())
