from fastapi import APIRouter

from app.core.database import SessionDependency
from app.modules.health.schemas import HealthRead
from app.modules.health.service import comprobar_base

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthRead)
async def live() -> dict[str, str]:
    return {"estado": "vivo"}


@router.get("/ready", response_model=HealthRead)
async def ready(session: SessionDependency) -> dict[str, str]:
    return await comprobar_base(session)
