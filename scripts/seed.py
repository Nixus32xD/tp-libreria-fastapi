"""Load deterministic demonstration data without overwriting an existing complete seed."""

import argparse
import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import (
    Autor,
    Cliente,
    Editorial,
    Genero,
    Libro,
    LibroAutor,
    PerfilCliente,
    RenglonVenta,
    Venta,
)


class SeedError(ValueError):
    """Safe, user-facing failure that never contains a database URL or driver text."""


# These identifiers are constants owned by this utility, never user input.
TRUNCATE_SQL = (
    "TRUNCATE renglon_venta, venta, perfil_cliente, libro_autor, libro, "
    "cliente, autor, genero, editorial RESTART IDENTITY CASCADE"
)
TABLE_MODELS = (
    Editorial,
    Genero,
    Autor,
    Libro,
    LibroAutor,
    Cliente,
    PerfilCliente,
    Venta,
    RenglonVenta,
)
IDENTITIES = (
    (Editorial, "nombre", {1: "Sudamericana"}),
    (Genero, "nombre", {1: "Novela", 2: "Cuentos"}),
    (
        Autor,
        "nombre",
        {
            1: "Julio Cortázar",
            2: "Jorge Luis Borges",
            3: "Adolfo Bioy Casares",
            4: "Silvina Ocampo",
            5: "Ricardo Piglia",
        },
    ),
    (Libro, "isbn", {index: f"978-950-00-000{index}-{index}" for index in range(1, 5)}),
    (Cliente, "email", {1: "ana@example.com", 2: "tomas@example.com"}),
)


def validate_database_url(database_url: str) -> None:
    try:
        url = make_url(database_url)
    except (ArgumentError, TypeError, ValueError):
        raise SeedError("DATABASE_URL debe indicar PostgreSQL con postgresql+asyncpg.") from None
    if url.drivername != "postgresql+asyncpg" or not url.database:
        raise SeedError("DATABASE_URL debe indicar PostgreSQL con postgresql+asyncpg.")


async def has_complete_seed(session) -> bool:
    for model, column, expected in IDENTITIES:
        rows = await session.execute(
            select(model.id, getattr(model, column)).where(model.id.in_(expected))
        )
        if dict(rows.all()) != expected:
            return False
    authorships = set(
        (await session.execute(select(LibroAutor.libro_id, LibroAutor.autor_id))).all()
    )
    return {(1, 1), (2, 2), (3, 3), (3, 4), (4, 5)}.issubset(authorships)


def demonstration_entities() -> list:
    editorial = Editorial(id=1, nombre="Sudamericana", pais="Argentina")
    genres = {
        1: Genero(id=1, nombre="Novela"),
        2: Genero(id=2, nombre="Cuentos"),
    }
    authors = {
        index: Autor(id=index, nombre=name, nacionalidad="Argentina")
        for index, name in IDENTITIES[2][2].items()
    }
    books = []
    for index, title, price, genre_id, author_ids in [
        (1, "Rayuela", "25000.00", 1, [1]),
        (2, "Ficciones", "18000.00", 2, [2]),
        (3, "Los que aman, odian", "21000.00", 1, [3, 4]),
        (4, "Respiración artificial", "27000.00", 1, [5]),
    ]:
        books.append(
            Libro(
                id=index,
                isbn=IDENTITIES[3][2][index],
                titulo=title,
                precio=Decimal(price),
                stock=20,
                editorial=editorial,
                genero=genres[genre_id],
                autorias=[
                    LibroAutor(
                        autor=authors[author_id],
                        rol="coautor" if len(author_ids) > 1 else "autor",
                        orden=order,
                    )
                    for order, author_id in enumerate(author_ids, 1)
                ],
            )
        )
    return [
        editorial,
        *genres.values(),
        *authors.values(),
        *books,
        Cliente(id=1, nombre="Ana Pérez", email="ana@example.com"),
        Cliente(id=2, nombre="Tomás Ríos", email="tomas@example.com"),
    ]


async def seed(database_url: str, reset: bool = False) -> None:
    """Commit all initial data atomically; only explicit reset may erase existing rows."""
    validate_database_url(database_url)
    engine = create_async_engine(database_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            async with session.begin():
                if reset:
                    await session.execute(text(TRUNCATE_SQL))
                populated = False
                for model in TABLE_MODELS:
                    if await session.scalar(select(func.count()).select_from(model)):
                        populated = True
                        break
                if populated:
                    if await has_complete_seed(session):
                        return
                    raise SeedError(
                        "La base esta parcialmente poblada o es ajena al seed; no se modifico. "
                        "Revisala o usa --reset --confirm-reset en una base exclusiva del TP."
                    )
                session.add_all(demonstration_entities())
                await session.flush()
                # Explicit ids are deterministic even after rolled-back inserts advanced a sequence.
                # All names below are fixed by the program, not supplied by the user.
                for table in ("editorial", "genero", "autor", "libro", "cliente"):
                    await session.execute(
                        text(
                            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                            f"(SELECT MAX(id) FROM {table}), true)"
                        )
                    )
    except SQLAlchemyError:
        raise SeedError(
            "No se pudo cargar la base. Revisa DATABASE_URL y ejecuta alembic upgrade head."
        ) from None
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Cargar datos iniciales del TP de libreria.")
    parser.add_argument("--reset", action="store_true", help="Borrar datos de la base indicada.")
    parser.add_argument(
        "--confirm-reset", action="store_true", help="Confirmar el borrado explicitamente."
    )
    args = parser.parse_args()
    try:
        if args.reset != args.confirm_reset:
            raise SeedError("El reinicio requiere --reset y --confirm-reset juntos.")
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise SeedError("Defini DATABASE_URL en el entorno o en .env para PostgreSQL.")
        asyncio.run(seed(database_url, reset=args.reset))
    except (SeedError, OSError):
        # Never print driver exceptions, credentials or tracebacks to a terminal log.
        error = sys.exception()
        message = str(error) if isinstance(error, SeedError) else "No se pudo conectar a la base."
        print(f"Error: {message}", file=sys.stderr)
        return 1
    print("Datos iniciales listos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
