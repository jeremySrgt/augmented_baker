from fastapi import Request

from app.services.chat_service import ChatService
from app.services.health_service import HealthService


def get_health_service() -> HealthService:
    return HealthService()


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service
