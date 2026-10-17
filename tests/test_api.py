import os

import httpx
import pytest
from asgi_lifespan import LifespanManager
from dotenv import load_dotenv

from app.main import create_app


@pytest.mark.asyncio
async def test_crear_editorial(monkeypatch):
    load_dotenv()
    monkeypatch.setenv('DATABASE_URL', os.environ['TEST_DATABASE_URL'])
    async with LifespanManager(create_app()) as manager:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=manager.app), base_url='http://test') as client:
            response = await client.post('/editoriales/', json={'nombre': 'Editorial RED', 'pais': 'Argentina'})
    assert response.status_code == 201, response.text
