"""聚合全部 API 路由。"""

from fastapi import APIRouter

from app.api.routes import blood_pressure, health, messages, ocr, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(blood_pressure.router)
api_router.include_router(ocr.router)
api_router.include_router(messages.router)
api_router.include_router(users.router)

