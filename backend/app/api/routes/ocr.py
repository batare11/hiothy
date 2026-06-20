"""图片 OCR 接口。"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.dependencies import get_mini_user_id
from app.core.config import settings
from app.services.ocr import recognize_blood_pressure

router = APIRouter(prefix="/ocr", tags=["ocr"])
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


@router.post("/blood-pressure")
async def ocr_blood_pressure(
    file: UploadFile = File(...),
    _: str = Depends(get_mini_user_id),
) -> dict:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="仅支持 JPG、PNG、WebP、BMP 图片")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="图片大小超出限制")
    try:
        data = recognize_blood_pressure(content)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"图片识别失败，请调整拍摄角度或手动录入：{exc}",
        ) from exc
    return {"code": 0, "message": "识别完成，请人工核对", "data": data}
