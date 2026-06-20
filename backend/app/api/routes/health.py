from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check() -> dict:
    return {"code": 0, "message": "服务运行正常", "data": {"status": "ok"}}

