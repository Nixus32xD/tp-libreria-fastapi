"""Seed integration tests use a dedicated, explicitly named PostgreSQL test database."""

import os
import subprocess
import sys
from decimal import Decimal

import pytest
from dotenv import load_dotenv
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Cliente, Editorial, Libro, RenglonVenta, Venta
from scripts.seed import SeedError, seed


@pytest.fixture
async def seed_database_url():
    load_dotenv()
    url = os.getenv("SEED_TEST_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.fail("Falta TEST_DATABASE_URL para las pruebas PostgreSQL del seed.")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+asyncpg" or not (parsed.database or "").endswith("_test"):
        pytest.fail("La base del seed debe usar PostgreSQL asyncpg y terminar en _test.")
    production = os.getenv("DATABASE_URL")
    if production and make_url(production).set(drivername=parsed.drivername) == parsed:
        pytest.fail("Las pruebas del seed requieren una base distinta de DATABASE_URL.")
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.execute(text(
            "TRUNCATE renglon_venta, venta, perfil_cliente, libro_autor, libro, "
            "cliente, autor, genero, editorial RESTART IDENTITY CASCADE"
        ))
    await engine.dispose()
    return url


async def test_seed_initial_data_is_deterministic_and_creates_no_sales(seed_database_url):
    await seed(seed_database_url)
    engine = create_async_engine(seed_database_url)
    try:
        async with async_sessionmaker(engine)() as session:
            books = (await session.scalars(select(Libro).order_by(Libro.id))).all()
            assert [(book.id, book.titulo, book.precio) for book in books] == [
                (1, "Rayuela", Decimal("25000.00")),
                (2, "Ficciones", Decimal("18000.00")),
                (3, "Los que aman, odian", Decimal("21000.00")),
                (4, "Respiración artificial", Decimal("27000.00")),
            ]
            customer = await session.get(Cliente, 2)
            assert (customer.nombre, customer.email) == ("Tomás Ríos", "tomas@example.com")
            assert await session.scalar(select(func.count()).select_from(Venta)) == 0
    finally:
        await engine.dispose()


async def test_repetition_preserves_edited_prices_and_registered_sales(seed_database_url):
    await seed(seed_database_url)
    engine = create_async_engine(seed_database_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            book = await session.get(Libro, 1)
            book.precio = Decimal("30000.00")
            session.add(Venta(
                cliente_id=1, total=Decimal("25000.00"),
                renglones=[RenglonVenta(libro_id=1, cantidad=1, precio_unitario=Decimal("25000.00"))],
            ))
            await session.commit()
        await seed(seed_database_url)
        async with async_sessionmaker(engine)() as session:
            assert (await session.get(Libro, 1)).precio == Decimal("30000.00")
            assert await session.scalar(select(func.count()).select_from(Libro)) == 4
            assert await session.scalar(select(func.count()).select_from(Venta)) == 1
            assert (await session.get(RenglonVenta, 1)).precio_unitario == Decimal("25000.00")
    finally:
        await engine.dispose()


async def test_partial_database_is_rejected_without_changing_existing_rows(seed_database_url):
    engine = create_async_engine(seed_database_url)
    try:
        async with async_sessionmaker(engine)() as session:
            session.add(Editorial(nombre="Existente", pais="Argentina"))
            await session.commit()
        with pytest.raises(SeedError, match="parcial|ajena"):
            await seed(seed_database_url)
        async with async_sessionmaker(engine)() as session:
            assert await session.scalar(select(func.count()).select_from(Editorial)) == 1
            assert await session.scalar(select(func.count()).select_from(Libro)) == 0
    finally:
        await engine.dispose()


async def test_explicit_reset_restores_initial_ids_and_data(seed_database_url):
    await seed(seed_database_url)
    engine = create_async_engine(seed_database_url)
    try:
        async with async_sessionmaker(engine)() as session:
            book = await session.get(Libro, 1)
            book.precio = Decimal("1.00")
            session.add(Venta(cliente_id=1, total=Decimal("0.00")))
            await session.commit()
        await seed(seed_database_url, reset=True)
        async with async_sessionmaker(engine)() as session:
            assert (await session.get(Libro, 1)).precio == Decimal("25000.00")
            assert await session.scalar(select(func.count()).select_from(Venta)) == 0
    finally:
        await engine.dispose()


@pytest.mark.parametrize("flags", [["--reset"], ["--confirm-reset"]])
def test_cli_requires_both_reset_flags_before_connecting(flags):
    result = subprocess.run(
        [sys.executable, "-m", "scripts.seed", *flags],
        env={**os.environ, "DATABASE_URL": "postgresql+asyncpg://secret:password@invalid/db"},
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "--reset" in result.stderr and "--confirm-reset" in result.stderr
    assert "secret" not in result.stderr and "password" not in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("url", ["sqlite+aiosqlite:///demo.db", "no-es-una-url"])
async def test_invalid_database_urls_fail_with_a_safe_message(url):
    with pytest.raises(SeedError, match="PostgreSQL"):
        await seed(url)
