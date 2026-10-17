from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models  # noqa: F401 - registra todas las tablas y sus relaciones
from app.core.config import get_settings
from app.modules.health.router import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=settings.sql_echo, pool_pre_ping=True)
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Librería de barrio",
        description="Catálogo, clientes y ventas con FastAPI y PostgreSQL.",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.include_router(health_router)
    return application


app = create_app()
