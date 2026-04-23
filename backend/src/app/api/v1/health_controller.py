from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_health_service
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter(tags=["health"])

HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]


@router.get("/health", response_model=HealthResponse)
def get_health(service: HealthServiceDep) -> HealthResponse:
    return service.check()
