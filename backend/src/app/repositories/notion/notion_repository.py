import logging

from notion_client import APIResponseError, AsyncClient
from notion_client.errors import HTTPResponseError, RequestTimeoutError

from app.repositories.notion._flatten import flatten_page
from app.repositories.notion.client import get_notion_client
from app.repositories.notion.databases import (
    COMMANDES_FOURNISSEURS,
    STOCK_INGREDIENTS,
    NotionDatabase,
)

logger = logging.getLogger(__name__)

_MIN_LIMIT = 1
_MAX_LIMIT = 100


class NotionUnavailable(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotionRepository:
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def query(
        self,
        database: NotionDatabase,
        title_contains: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        page_size = max(_MIN_LIMIT, min(_MAX_LIMIT, limit))
        payload: dict = {
            "data_source_id": database.data_source_id,
            "page_size": page_size,
        }
        if title_contains:
            payload["filter"] = {
                "property": "title",
                "title": {"contains": title_contains},
            }

        try:
            response = await self._client.data_sources.query(**payload)
        except APIResponseError as exc:
            logger.warning("notion API error on %s: %s", database.name, exc.code)
            raise NotionUnavailable(f"Notion a refusé la requête ({exc.code})") from exc
        except (HTTPResponseError, RequestTimeoutError) as exc:
            logger.warning(
                "notion transport error on %s: %s", database.name, type(exc).__name__
            )
            raise NotionUnavailable("Notion injoignable") from exc

        return [flatten_page(page) for page in response.get("results", [])]

    async def create_page(
        self,
        database: NotionDatabase,
        properties: dict,
    ) -> dict:
        if database.database_id != COMMANDES_FOURNISSEURS.database_id:
            raise ValueError(
                f"create_page is only allowed on {COMMANDES_FOURNISSEURS.name}, "
                f"got {database.name}"
            )
        try:
            return await self._client.pages.create(
                parent={"data_source_id": database.data_source_id},
                properties=properties,
            )
        except APIResponseError as exc:
            logger.warning("notion API error on %s create: %s", database.name, exc.code)
            raise NotionUnavailable(f"Notion a refusé la requête ({exc.code})") from exc
        except (HTTPResponseError, RequestTimeoutError) as exc:
            logger.warning(
                "notion transport error on %s create: %s",
                database.name,
                type(exc).__name__,
            )
            raise NotionUnavailable("Notion injoignable") from exc

    async def update_page(
        self,
        database: NotionDatabase,
        page_id: str,
        properties: dict,
    ) -> dict:
        if database.database_id != STOCK_INGREDIENTS.database_id:
            raise ValueError(
                f"update_page is only allowed on {STOCK_INGREDIENTS.name}, "
                f"got {database.name}"
            )
        try:
            return await self._client.pages.update(
                page_id=page_id,
                properties=properties,
            )
        except APIResponseError as exc:
            logger.warning("notion API error on %s update: %s", database.name, exc.code)
            raise NotionUnavailable(f"Notion a refusé la requête ({exc.code})") from exc
        except (HTTPResponseError, RequestTimeoutError) as exc:
            logger.warning(
                "notion transport error on %s update: %s",
                database.name,
                type(exc).__name__,
            )
            raise NotionUnavailable("Notion injoignable") from exc


notion_repository = NotionRepository(get_notion_client())


def get_notion_repository() -> NotionRepository:
    return notion_repository
