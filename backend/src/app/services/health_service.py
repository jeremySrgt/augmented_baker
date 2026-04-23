from datetime import UTC, datetime

from app import __version__
from app.config import settings
from app.schemas.health import HealthResponse


class HealthService:
    def check(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            env=settings.app_env,
            version=__version__,
        )
