from functools import lru_cache

from app.services.chat_service import ChatService
from app.services.health_service import HealthService


def get_health_service() -> HealthService:
    return HealthService()


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    return ChatService()
