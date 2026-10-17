"""Contratos HTTP, integridad y atomicidad en PostgreSQL real."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import text


def own_conflict(response):
    assert response.status_code == 409, response.text
    assert isinstance(response.json()["detail"], str)
    for internal in (
        "asyncpg",
        "IntegrityError",
        "Traceback",
        "INSERT INTO",
        "foreign key",
        "unique constraint",
    ):
        assert internal not in response.text


async def test_crear_editorial(client):
    response = await client.post("/editoriales/", json={"nombre": "Sur", "pais": "Argentina"})
    assert response.status_code == 201, response.text
    assert response.json() == {"id": 1, "nombre": "Sur", "pais": "Argentina"}
    assert (await client.get("/health/ready")).status_code == 200


@pytest.mark.parametrize("resource", ["editoriales", "autores", "libros", "clientes", "ventas"])
async def test_c01_route_validation_and_missing(client, resource):
    assert (await client.get(f"/{resource}/no-es-entero")).status_code == 422
    assert (await client.get(f"/{resource}/99999")).status_code == 404


async def test_partial_patch_preserves_omitted_fields(client, catalog):
    for resource, patch, preserved in [
        ("editoriales", {"pais": "Uruguay"}, {"nombre": "Sur"}),
        ("autores", {"nacionalidad": "Uruguay"}, {"nombre": "Julio"}),
        ("clientes", {"nombre": "Ana María"}, {"email": "c0@example.com"}),
        ("libros", {"titulo": "Rayuela revisada"}, {"isbn": "978-test-0", "stock": 10}),
    ]:
        response = await client.patch(f"/{resource}/1", json=patch)
        assert response.status_code == 200, response.text
        for key, value in (patch | preserved).items():
            assert response.json()[key] == value
        assert (await client.patch(f"/{resource}/99999", json=patch)).status_code == 404
    response = await client.patch("/libros/1", json={"genero_id": None})
    assert response.status_code == 200
    assert response.json()["genero"] is None
    assert response.json()["genero_id"] is None
    assert len(response.json()["autores"]) == 1
    assert (await client.patch("/libros/1", json={})).json() == response.json()


async def test_c02_unique_values_and_rollback(client, catalog, book_body):
    book_body["isbn"] = catalog["books"][0]["isbn"]
    for path, body in [
        ("/libros/", book_body),
        ("/clientes/", {"nombre": "Otra", "email": "c0@example.com"}),
        ("/editoriales/", {"nombre": "Sur", "pais": "Chile"}),
        ("/generos/", {"nombre": "Novela"}),
    ]:
        own_conflict(await client.post(path, json=body))
    own_conflict(await client.patch("/libros/2", json={"isbn": "978-test-0"}))
    own_conflict(await client.patch("/clientes/2", json={"email": "c0@example.com"}))
    assert (await client.get("/clientes/2")).json()["email"] == "c1@example.com"


async def test_c03_profile_one_to_one(client, catalog):
    assert (await client.get("/clientes/1")).json()["perfil"] is None
    body = {"telefono": "2615551234", "direccion": "San Martín 100"}
    created = await client.post("/clientes/1/perfil", json=body)
    assert created.status_code == 201, created.text
    own_conflict(await client.post("/clientes/1/perfil", json=body))
    assert (await client.get("/clientes/1")).json()["perfil"] == created.json()
    assert (await client.post("/clientes/99999/perfil", json=body)).status_code == 404


@pytest.mark.parametrize("field", ["editorial_id", "genero_id", "autor_id"])
async def test_c04_book_foreign_keys_atomic(client, application, catalog, book_body, field):
    if field == "autor_id":
        book_body["autores"].append({"autor_id": 99999, "rol": "traductor", "orden": 2})
    else:
        book_body[field] = 99999
    own_conflict(await client.post("/libros/", json=book_body))
    assert len((await client.get("/libros/")).json()) == 4
    async with application.state.engine.connect() as connection:
        assert await connection.scalar(text("SELECT count(*) FROM libro_autor")) == 13


@pytest.mark.parametrize("field", ["cliente_id", "libro_id"])
async def test_c05_sale_foreign_keys_atomic(client, application, catalog, sale_body, field):
    if field == "cliente_id":
        sale_body[field] = 99999
    else:
        sale_body["renglones"][1][field] = 99999
    own_conflict(await client.post("/ventas/", json=sale_body))
    assert (await client.get("/ventas/")).json() == []
    async with application.state.engine.connect() as connection:
        assert await connection.scalar(text("SELECT count(*) FROM renglon_venta")) == 0


async def test_c06_sale_snapshot_total_timezone_immutable(client, catalog, sale_body):
    response = await client.post("/ventas/", json=sale_body)
    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["total"] == "77000.00"
    assert datetime.fromisoformat(sale["fecha"].replace("Z", "+00:00")).utcoffset() is not None
    assert sale["cliente"]["email"] == "c0@example.com"
    assert [(r["precio_unitario"], r["subtotal"]) for r in sale["renglones"]] == [
        ("25000.00", "50000.00"),
        ("27000.00", "27000.00"),
    ]
    assert (await client.patch("/libros/1", json={"precio": "30000.00"})).status_code == 200
    assert (await client.get(f"/ventas/{sale['id']}")).json() == sale
    assert (await client.patch(f"/ventas/{sale['id']}", json={"total": "1.00"})).status_code == 405
    exact = await client.post(
        "/ventas/", json={"cliente_id": 2, "renglones": [{"libro_id": 2, "cantidad": 3}]}
    )
    assert exact.status_code == 201
    assert Decimal(exact.json()["total"]) == Decimal("54000.30")


@pytest.mark.parametrize(
    "path",
    [
        "/editoriales/",
        "/generos/",
        "/autores/",
        "/clientes/",
        "/libros/",
        "/ventas/",
        "/editoriales/1/libros",
        "/generos/1/libros",
        "/autores/1/libros",
        "/clientes/1/ventas",
    ],
)
async def test_all_lists_paginate(client, catalog, path):
    for query in ("limit=0", "limit=101", "offset=-1", "limit=no"):
        assert (await client.get(f"{path}?{query}")).status_code == 422
    response = await client.get(f"{path}?limit=1&offset=0")
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 1
    assert (await client.get(f"{path}?limit=1&offset=999")).json() == []


async def test_nested_lists_and_c08_bound_case_insensitive_search(client, catalog):
    for path in ("/editoriales/1/libros", "/generos/1/libros"):
        assert len((await client.get(path)).json()) == 4
    books = (await client.get("/autores/1/libros")).json()
    assert len(books) == 4
    assert all(row["rol"] == "coautor" and row["orden"] == 1 for row in books)
    for path in (
        "/editoriales/99999/libros",
        "/generos/99999/libros",
        "/autores/99999/libros",
        "/clientes/99999/ventas",
    ):
        assert (await client.get(path)).status_code == 404
    assert len((await client.get("/libros/", params={"titulo": "RaYu"})).json()) == 1
    assert (await client.get("/libros/", params={"titulo": "' OR '1'='1"})).json() == []
    assert (await client.get("/libros/", params={"genero_id": 99999})).json() == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("precio", "0"),
        ("precio", "-1"),
        ("precio", "1.001"),
        ("precio", "100000000.00"),
        ("stock", -1),
        ("stock", 2147483648),
        ("titulo", ""),
        ("id", 77),
        ("editorial_id", None),
    ],
)
async def test_invalid_book_dto(client, catalog, book_body, field, value):
    book_body[field] = value
    assert (await client.post("/libros/", json=book_body)).status_code == 422


@pytest.mark.parametrize(
    "authors",
    [
        [{"autor_id": 1, "rol": "desconocido", "orden": 1}],
        [{"autor_id": 1, "rol": "autor", "orden": 0}],
        [
            {"autor_id": 1, "rol": "autor", "orden": 1},
            {"autor_id": 1, "rol": "coautor", "orden": 2},
        ],
    ],
)
async def test_invalid_authorship_dto(client, catalog, book_body, authors):
    book_body["autores"] = authors
    assert (await client.post("/libros/", json=book_body)).status_code == 422


@pytest.mark.parametrize(
    "patch",
    [
        {"titulo": None},
        {"precio": None},
        {"stock": None},
        {"isbn": None},
        {"editorial_id": None},
        {"autores": None},
        {"precio": "1.001"},
    ],
)
async def test_patch_rejects_null_required(client, catalog, patch):
    assert (await client.patch("/libros/1", json=patch)).status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {"cliente_id": 1, "renglones": []},
        {"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": 0}]},
        {"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": 2147483648}]},
        {
            "cliente_id": 1,
            "renglones": [{"libro_id": 1, "cantidad": 1}, {"libro_id": 1, "cantidad": 2}],
        },
        {"cliente_id": 1, "total": "1.00", "renglones": [{"libro_id": 1, "cantidad": 1}]},
        {"cliente_id": 1, "fecha": "2026-01-01", "renglones": [{"libro_id": 1, "cantidad": 1}]},
        {"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": 1, "precio_unitario": "1.00"}]},
    ],
)
async def test_sale_dto_excludes_server_fields(client, catalog, body):
    assert (await client.post("/ventas/", json=body)).status_code == 422


async def test_sale_total_overflow_is_422(client, catalog, application):
    async with application.state.engine.begin() as connection:
        await connection.execute(text("UPDATE libro SET precio=99999999.99 WHERE id=1"))
    response = await client.post(
        "/ventas/", json={"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": 101}]}
    )
    assert response.status_code == 422, response.text
    assert (await client.get("/ventas/")).json() == []


@pytest.mark.parametrize("offset", ["9223372036854775808", "1000000000000000000000000000000"])
async def test_offset_outside_postgresql_bigint_returns_422(client, offset):
    response = await client.get("/libros/", params={"offset": offset})
    assert response.status_code == 422, response.text


async def test_authorship_patch_replaces_and_updates_atomically(client, catalog):
    body = {
        "autores": [
            {"autor_id": 1, "rol": "traductor", "orden": 2},
            {"autor_id": 2, "rol": "autor", "orden": 1},
        ]
    }
    response = await client.patch("/libros/1", json=body)
    assert response.status_code == 200, response.text
    authors = response.json()["autores"]
    assert [(row["autor_id"], row["rol"], row["orden"]) for row in authors] == [
        (2, "autor", 1),
        (1, "traductor", 2),
    ]
    assert response.json()["titulo"] == "Rayuela"
    removed = await client.patch(
        "/libros/1", json={"autores": [{"autor_id": 2, "rol": "coautor", "orden": 1}]}
    )
    assert removed.status_code == 200, removed.text
    assert [row["autor_id"] for row in removed.json()["autores"]] == [2]
    books_of_original = (await client.get("/autores/1/libros")).json()
    assert all(row["libro"]["id"] != 1 for row in books_of_original)


async def test_authorship_patch_conflict_rolls_back_all_changes(client, catalog):
    before = (await client.get("/libros/2")).json()
    response = await client.patch(
        "/libros/2",
        json={
            "titulo": "No debe persistir",
            "autores": [{"autor_id": 99999, "rol": "autor", "orden": 1}],
        },
    )
    own_conflict(response)
    assert (await client.get("/libros/2")).json() == before


@pytest.mark.parametrize("genre", [{}, {"genero_id": None}])
async def test_book_optional_genre_can_be_omitted_or_null(client, catalog, book_body, genre):
    book_body.pop("genero_id")
    response = await client.post("/libros/", json=book_body | genre)
    assert response.status_code == 201, response.text
    assert response.json()["genero"] is None
    assert response.json()["genero_id"] is None
