from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app import __version__
from app.api.v1 import health_controller
from app.api.v1 import router as v1_router
from app.config import settings
from app.core.logging import configure_logging
from app.repositories.notion.client import notion_client
from app.services.chat_service import ChatService


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings.MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(settings.MEMORY_DB_PATH)) as saver:
        application.state.chat_service = ChatService(checkpointer=saver)
        try:
            yield
        finally:
            await notion_client.aclose()


def create_app() -> FastAPI:
    configure_logging()

    application = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        lifespan=lifespan,
    )

    application.include_router(health_controller.router)
    application.include_router(v1_router.router)

    return application


app = create_app()
