from fastapi import APIRouter

from app.api.v1 import chat_controller, health_controller

router = APIRouter(prefix="/v1")
router.include_router(health_controller.router)
router.include_router(chat_controller.router)
