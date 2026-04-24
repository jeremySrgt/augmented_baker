from datetime import UTC, datetime

from app import __version__
from app.config import settings
from app.schemas.health import HealthResponse


class HealthService:
    def check(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.APP_NAME,
            env=settings.app_env,
            version=__version__,
        )
