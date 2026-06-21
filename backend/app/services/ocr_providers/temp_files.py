"""供云端 AI 短时读取的不可猜测图片文件。"""

import time
import uuid
from pathlib import Path

from app.core.config import settings

CONTENT_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}


def _temp_dir() -> Path:
    directory = Path(settings.ocr_temp_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def cleanup_expired_files() -> None:
    now = time.time()
    max_age = max(settings.ocr_temp_file_ttl, 60)
    for path in _temp_dir().glob("*"):
        if path.is_file() and now - path.stat().st_mtime > max_age:
            path.unlink(missing_ok=True)


def create_temp_image(content: bytes, content_type: str) -> tuple[str, Path]:
    cleanup_expired_files()
    extension = CONTENT_EXTENSIONS.get(content_type, ".jpg")
    filename = f"{uuid.uuid4().hex}{extension}"
    path = _temp_dir() / filename
    path.write_bytes(content)
    return filename, path


def resolve_temp_image(filename: str) -> Path | None:
    if not filename or Path(filename).name != filename:
        return None
    path = _temp_dir() / filename
    if not path.is_file():
        return None
    if time.time() - path.stat().st_mtime > max(settings.ocr_temp_file_ttl, 60):
        path.unlink(missing_ok=True)
        return None
    return path


def delete_temp_image(path: Path | None) -> None:
    if path:
        path.unlink(missing_ok=True)
