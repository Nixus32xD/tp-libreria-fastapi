"""C-07: consultas reales constantes y escrituras delegadas a PostgreSQL."""

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event


@contextmanager
def emitted_sql(application):
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(application.state.engine.sync_engine, "before_cursor_execute", capture)
    try:
        yield statements
    finally:
        event.remove(application.state.engine.sync_engine, "before_cursor_execute", capture)


async def test_c07_book_and_sale_detail_constant_queries(client, application, catalog, sale_body):
    small = await client.post(
        "/ventas/", json={"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": 1}]}
    )
    large = await client.post("/ventas/", json=sale_body)
    assert small.status_code == large.status_code == 201
    evidence = [
        "C-07 | SQL real capturado con before_cursor_execute de SQLAlchemy.",
        "PostgreSQL; fixtures aisladas migradas con Alembic.",
    ]
    for path, size in [
        ("/libros/1", "1 autor"),
        ("/libros/2", "4 autores"),
        (f"/ventas/{small.json()['id']}", "1 renglón"),
        (f"/ventas/{large.json()['id']}", "2 renglones"),
    ]:
        with emitted_sql(application) as statements:
            response = await client.get(path)
        assert response.status_code == 200, response.text
        selects = [sql for sql in statements if sql.lstrip().upper().startswith("SELECT")]
        assert len(selects) == 2, (path, selects)
        evidence.extend([f"\nGET {path} ({size}) -> HTTP 200; SELECT = {len(selects)}", *selects])
    output = Path(__file__).resolve().parents[1] / "tmp" / "evidencia-c07.txt"
    output.parent.mkdir(exist_ok=True)
    output.write_text("\n".join(evidence), encoding="utf-8")


async def test_book_write_has_no_fk_or_uniqueness_prechecks(
    client, application, catalog, book_body
):
    with emitted_sql(application) as statements:
        created = await client.post("/libros/", json=book_body)
    assert created.status_code == 201, created.text
    commands = [sql.lstrip().split()[0].upper() for sql in statements]
    assert commands[0] == "INSERT", statements
    with emitted_sql(application) as duplicate_statements:
        duplicate = await client.post("/libros/", json=book_body)
    assert duplicate.status_code == 409
    assert not any(sql.lstrip().upper().startswith("SELECT") for sql in duplicate_statements)


async def test_isbn_and_email_conflicts_do_not_query_first(client, application, catalog):
    with emitted_sql(application) as statements:
        response = await client.post(
            "/clientes/", json={"nombre": "Otra", "email": "c0@example.com"}
        )
    assert response.status_code == 409
    assert statements[0].lstrip().upper().startswith("INSERT")
    assert not any(sql.lstrip().upper().startswith("SELECT") for sql in statements)
