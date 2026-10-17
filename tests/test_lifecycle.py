"""Primer contrato ejecutable del ciclo de vida y salud de la API."""

import httpx
from asgi_lifespan import LifespanManager

from app.main import create_app


async def test_liveness_responde_sin_consultar_postgresql(monkeypatch):
    # Un puerto sin servidor prueba que liveness no depende de la base.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://nadie@127.0.0.1:1/ausente")
    app = create_app()
    async with LifespanManager(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"estado": "vivo"}


async def test_readiness_informa_indisponibilidad_sin_filtrar_datos(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://nadie@127.0.0.1:1/ausente")
    app = create_app()
    async with LifespanManager(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/ready")
    assert response.status_code == 503
    assert isinstance(response.json()["detail"], str)
    for internal in ("nadie", "127.0.0.1", "SELECT", "Traceback", "asyncpg"):
        assert internal not in response.text
