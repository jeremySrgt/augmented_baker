from notion_client import AsyncClient

from app.config import settings

notion_client = AsyncClient(auth=settings.NOTION_TOKEN.get_secret_value())


def get_notion_client() -> AsyncClient:
    return notion_client
