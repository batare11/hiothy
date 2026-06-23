"""图片 OCR 接口。"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.dependencies import get_mini_user_id
from app.core.config import settings
from app.core.database import get_db
from app.services.access_control import Permission, require_permission
from app.services.ocr_providers import recognize_with_provider
from app.services.ocr_providers.temp_files import resolve_temp_image
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ocr", tags=["ocr"])
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


@router.api_route(
    "/temp/{filename}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
def get_temporary_ocr_image(filename: str) -> FileResponse:
    path = resolve_temp_image(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="临时图片不存在或已过期")
    return FileResponse(
        path,
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.post("/blood-pressure")
async def ocr_blood_pressure(
    file: UploadFile = File(...),
    engine: str = Query(
        default="rapid",
        pattern="^(rapid|doubao|glm|auto)$",
    ),
    mini_user_id: str = Depends(get_mini_user_id),
    db: Session = Depends(get_db),
) -> dict:
    if engine != "rapid":
        require_permission(db, mini_user_id, Permission.CLOUD_OCR)
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="仅支持 JPG、PNG、WebP、BMP 图片")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="图片大小超出限制")
    try:
        data = await recognize_with_provider(
            content,
            file.content_type or "image/jpeg",
            engine,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"图片识别失败，请调整拍摄角度或手动录入：{exc}",
        ) from exc
    return {"code": 0, "message": "识别完成，请人工核对", "data": data}
