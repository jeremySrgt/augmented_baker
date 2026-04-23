from fastapi import FastAPI

from app import __version__
from app.api.v1 import health_controller
from app.api.v1 import router as v1_router
from app.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
    )

    application.include_router(health_controller.router)
    application.include_router(v1_router.router)

    return application


app = create_app()
