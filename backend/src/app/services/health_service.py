from datetime import UTC, datetime

from app import __version__
from app.config import settings
from app.schemas.health import HealthResponse


class HealthService:
    @staticmethod
    def check() -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.APP_NAME,
            env=settings.ENV,
            version=__version__,
        )
