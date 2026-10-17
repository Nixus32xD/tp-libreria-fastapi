"""PostgreSQL enforces these guarantees even when SQL bypasses every HTTP DTO."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scripts.seed import seed


@pytest.fixture
async def constraint_session(test_database_url):
    # The shared fixture validates isolation and applies Alembic before any reset.
    url = test_database_url
    await seed(url, reset=True)
    engine = create_async_engine(url)
    try:
        async with async_sessionmaker(engine)() as session:
            async with session.begin():
                await session.execute(
                    text(
                        "INSERT INTO venta (cliente_id, fecha, total) "
                        "VALUES (1, CURRENT_TIMESTAMP, 0)"
                    )
                )
                await session.execute(
                    text(
                        "INSERT INTO perfil_cliente (cliente_id, telefono, direccion) "
                        "VALUES (1, '123', 'Direccion de prueba')"
                    )
                )
                yield session
                await session.rollback()
    finally:
        await engine.dispose()


BOOK_INSERT = (
    "INSERT INTO libro (isbn, titulo, precio, stock, editorial_id, genero_id) "
    "VALUES (:isbn, 'Prueba DB', :precio, :stock, :editorial_id, :genero_id)"
)
AUTHORSHIP_INSERT = (
    "INSERT INTO libro_autor (libro_id, autor_id, rol, orden) "
    "VALUES (:libro_id, :autor_id, :rol, :orden)"
)
LINE_INSERT = (
    "INSERT INTO renglon_venta (venta_id, libro_id, cantidad, precio_unitario) "
    "VALUES (:venta_id, :libro_id, :cantidad, :precio_unitario)"
)
BOOK = {"isbn": "isbn-prueba", "precio": "10.00", "stock": 1, "editorial_id": 1, "genero_id": 1}
AUTHORSHIP = {"libro_id": 1, "autor_id": 2, "rol": "autor", "orden": 1}
LINE = {"venta_id": 1, "libro_id": 1, "cantidad": 1, "precio_unitario": "10.00"}


@pytest.mark.parametrize(
    "statement, params",
    [
        (BOOK_INSERT, {**BOOK, "precio": "0"}),
        (BOOK_INSERT, {**BOOK, "precio": "-0.01"}),
        (BOOK_INSERT, {**BOOK, "stock": -1}),
        (AUTHORSHIP_INSERT, {**AUTHORSHIP, "orden": 0}),
        (AUTHORSHIP_INSERT, {**AUTHORSHIP, "orden": -1}),
        (AUTHORSHIP_INSERT, {**AUTHORSHIP, "rol": "editor"}),
        (AUTHORSHIP_INSERT, {**AUTHORSHIP, "rol": "AUTOR"}),
        ("INSERT INTO venta (cliente_id, fecha, total) VALUES (1, CURRENT_TIMESTAMP, -0.01)", {}),
        (LINE_INSERT, {**LINE, "cantidad": 0}),
        (LINE_INSERT, {**LINE, "cantidad": -1}),
        (LINE_INSERT, {**LINE, "precio_unitario": "0"}),
        (LINE_INSERT, {**LINE, "precio_unitario": "-0.01"}),
    ],
)
async def test_checks_reject_invalid_rows_without_dto_validation(
    constraint_session, statement, params
):
    with pytest.raises(IntegrityError) as captured:
        async with constraint_session.begin_nested():
            await constraint_session.execute(text(statement), params)
    assert captured.value.orig.sqlstate == "23514"


@pytest.mark.parametrize(
    "statement, params",
    [
        ("INSERT INTO editorial (nombre, pais) VALUES ('Sudamericana', 'Argentina')", {}),
        ("INSERT INTO genero (nombre) VALUES ('Novela')", {}),
        (BOOK_INSERT, {**BOOK, "isbn": "978-950-00-0001-1"}),
        ("INSERT INTO cliente (nombre, email) VALUES ('Duplicado', 'ana@example.com')", {}),
        (
            "INSERT INTO perfil_cliente (cliente_id, telefono, direccion) "
            "VALUES (1, '456', 'Otra')",
            {},
        ),
        (AUTHORSHIP_INSERT, {**AUTHORSHIP, "autor_id": 1}),
    ],
)
async def test_uniqueness_is_enforced_by_postgresql(constraint_session, statement, params):
    with pytest.raises(IntegrityError) as captured:
        async with constraint_session.begin_nested():
            await constraint_session.execute(text(statement), params)
    assert captured.value.orig.sqlstate == "23505"


@pytest.mark.parametrize(
    "statement, params",
    [
        (BOOK_INSERT, {**BOOK, "editorial_id": 999999}),
        (BOOK_INSERT, {**BOOK, "genero_id": 999999}),
        (AUTHORSHIP_INSERT, {**AUTHORSHIP, "autor_id": 999999}),
        (AUTHORSHIP_INSERT, {**AUTHORSHIP, "libro_id": 999999}),
        (
            "INSERT INTO perfil_cliente (cliente_id, telefono, direccion) "
            "VALUES (999999, '456', 'Otra')",
            {},
        ),
        ("INSERT INTO venta (cliente_id, fecha, total) VALUES (999999, CURRENT_TIMESTAMP, 0)", {}),
        (LINE_INSERT, {**LINE, "libro_id": 999999}),
        (LINE_INSERT, {**LINE, "venta_id": 999999}),
    ],
)
async def test_foreign_keys_reject_missing_references(constraint_session, statement, params):
    with pytest.raises(IntegrityError) as captured:
        async with constraint_session.begin_nested():
            await constraint_session.execute(text(statement), params)
    assert captured.value.orig.sqlstate == "23503"


async def test_migrated_schema_has_an_index_for_every_foreign_key(constraint_session):
    connection = await constraint_session.connection()

    def check_indexes(sync_connection):
        inspector = inspect(sync_connection)
        keys_checked = 0
        for table in inspector.get_table_names():
            indexes = inspector.get_indexes(table)
            for foreign_key in inspector.get_foreign_keys(table):
                keys_checked += 1
                columns = foreign_key["constrained_columns"]
                assert any(index["column_names"][: len(columns)] == columns for index in indexes)
        return keys_checked

    assert await connection.run_sync(check_indexes) == 8
