"""Integración real sobre base explícita y separada, migrada exclusivamente con Alembic."""
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='session')
def test_database_url():
    load_dotenv(ROOT / '.env')
    value = os.getenv('TEST_DATABASE_URL')
    if not value:
        raise pytest.UsageError('Definí TEST_DATABASE_URL explícitamente')
    url = make_url(value)
    work = make_url(os.environ['DATABASE_URL']) if os.getenv('DATABASE_URL') else None
    if not url.database or not url.database.endswith('_test'):
        raise pytest.UsageError('La base de pruebas debe terminar en _test')
    if work and (url.host,url.port,url.database) == (work.host,work.port,work.database):
        raise pytest.UsageError('La base de pruebas debe ser distinta de DATABASE_URL')
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT,
                   env=dict(os.environ,DATABASE_URL=value),check=True,capture_output=True,text=True)
    return value

@pytest_asyncio.fixture
async def application(test_database_url, monkeypatch):
    from app.main import create_app
    monkeypatch.setenv('DATABASE_URL',test_database_url)
    app = create_app()
    async with LifespanManager(app):
        async with app.state.engine.begin() as connection:
            await connection.execute(text('TRUNCATE renglon_venta,venta,perfil_cliente,cliente,libro_autor,libro,autor,genero,editorial RESTART IDENTITY CASCADE'))
        yield app

@pytest_asyncio.fixture
async def client(application):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application),base_url='http://test') as session:
        yield session

@pytest_asyncio.fixture
async def catalog(client):
    async def post(path,body):
        response = await client.post(path,json=body)
        assert response.status_code == 201,response.text
        return response.json()
    editorial = await post('/editoriales/',{'nombre':'Sur','pais':'Argentina'})
    genero = await post('/generos/',{'nombre':'Novela'})
    authors = [await post('/autores/',{'nombre':name,'nacionalidad':'Argentina'}) for name in ('Julio','Jorge','Adolfo','Silvina')]
    books = []
    for index,price in enumerate(('25000.00','18000.10','21000.00','27000.00')):
        books.append(await post('/libros/',{'isbn':f'978-test-{index}','titulo':'Rayuela' if index==0 else f'Libro {index}',
            'precio':price,'stock':10,'editorial_id':editorial['id'],'genero_id':genero['id'],
            'autores':[{'autor_id':author['id'],'rol':'coautor','orden':i+1} for i,author in enumerate(authors[:1 if index==0 else 4])]}))
    customers = [await post('/clientes/',{'nombre':name,'email':f'c{i}@example.com'}) for i,name in enumerate(('Ana','Tomás'))]
    return {'editorial':editorial,'genero':genero,'authors':authors,'books':books,'customers':customers}

@pytest.fixture
def book_body(catalog):
    return {'isbn':'978-new','titulo':'Nuevo','precio':'10.25','stock':2,'editorial_id':catalog['editorial']['id'],
            'genero_id':catalog['genero']['id'],'autores':[{'autor_id':catalog['authors'][0]['id'],'rol':'autor','orden':1}]}

@pytest.fixture
def sale_body(catalog):
    return {'cliente_id':catalog['customers'][0]['id'],'renglones':[{'libro_id':catalog['books'][0]['id'],'cantidad':2},{'libro_id':catalog['books'][3]['id'],'cantidad':1}]}
