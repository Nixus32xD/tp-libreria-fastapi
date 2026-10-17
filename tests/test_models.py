"""Verify the relational contract independently of HTTP and application setup."""

from decimal import Decimal

import pytest
from sqlalchemy import CheckConstraint, Numeric, UniqueConstraint, inspect

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


@pytest.mark.parametrize(
    "model, table, columns",
    [
        (Editorial, "editorial", {"id", "nombre", "pais"}),
        (Genero, "genero", {"id", "nombre"}),
        (Autor, "autor", {"id", "nombre", "nacionalidad"}),
        (Libro, "libro", {"id", "isbn", "titulo", "precio", "stock", "editorial_id", "genero_id"}),
        (LibroAutor, "libro_autor", {"libro_id", "autor_id", "rol", "orden"}),
        (Cliente, "cliente", {"id", "nombre", "email"}),
        (PerfilCliente, "perfil_cliente", {"id", "cliente_id", "telefono", "direccion"}),
        (Venta, "venta", {"id", "cliente_id", "fecha", "total"}),
        (
            RenglonVenta,
            "renglon_venta",
            {"id", "venta_id", "libro_id", "cantidad", "precio_unitario"},
        ),
    ],
)
def test_required_tables_and_columns(model, table, columns):
    assert model.__tablename__ == table
    assert set(model.__table__.columns.keys()) == columns


@pytest.mark.parametrize(
    "model, column",
    [
        (Editorial, "nombre"),
        (Genero, "nombre"),
        (Libro, "isbn"),
        (Cliente, "email"),
        (PerfilCliente, "cliente_id"),
    ],
)
def test_unique_constraints_are_database_guarantees(model, column):
    unique_sets = {
        tuple(c.name for c in constraint.columns)
        for constraint in model.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    unique_sets.update(
        tuple(c.name for c in index.columns) for index in model.__table__.indexes if index.unique
    )
    assert (column,) in unique_sets


@pytest.mark.parametrize(
    "model, expression",
    [
        (Libro, "precio > 0"),
        (Libro, "stock >= 0"),
        (LibroAutor, "orden >= 1"),
        (LibroAutor, "rol IN ('autor', 'coautor', 'traductor', 'ilustrador')"),
        (Venta, "total >= 0"),
        (RenglonVenta, "cantidad > 0"),
        (RenglonVenta, "precio_unitario > 0"),
    ],
)
def test_business_checks_exist_in_database(model, expression):
    checks = {str(c.sqltext) for c in model.__table__.constraints if isinstance(c, CheckConstraint)}
    assert expression in checks


@pytest.mark.parametrize("model", [Libro, LibroAutor, PerfilCliente, Venta, RenglonVenta])
def test_every_foreign_key_has_an_explicit_index(model):
    table = model.__table__
    assert table.foreign_keys
    for foreign_key in table.foreign_keys:
        assert any(
            list(index.columns)[0].name == foreign_key.parent.name for index in table.indexes
        )


@pytest.mark.parametrize(
    "model, column, target",
    [
        (Libro, "editorial_id", "editorial.id"),
        (Libro, "genero_id", "genero.id"),
        (LibroAutor, "libro_id", "libro.id"),
        (LibroAutor, "autor_id", "autor.id"),
        (PerfilCliente, "cliente_id", "cliente.id"),
        (Venta, "cliente_id", "cliente.id"),
        (RenglonVenta, "venta_id", "venta.id"),
        (RenglonVenta, "libro_id", "libro.id"),
    ],
)
def test_foreign_keys_point_to_the_correct_owner(model, column, target):
    assert {fk.target_fullname for fk in model.__table__.c[column].foreign_keys} == {target}


@pytest.mark.parametrize(
    "model, attribute, inverse",
    [
        (Editorial, "libros", "editorial"),
        (Genero, "libros", "genero"),
        (Autor, "autorias", "autor"),
        (Libro, "editorial", "libros"),
        (Libro, "genero", "libros"),
        (Libro, "autorias", "libro"),
        (Libro, "renglones", "libro"),
        (LibroAutor, "libro", "autorias"),
        (LibroAutor, "autor", "autorias"),
        (Cliente, "perfil", "cliente"),
        (Cliente, "ventas", "cliente"),
        (PerfilCliente, "cliente", "perfil"),
        (Venta, "cliente", "ventas"),
        (Venta, "renglones", "venta"),
        (RenglonVenta, "venta", "renglones"),
        (RenglonVenta, "libro", "renglones"),
    ],
)
def test_relationships_are_bidirectional_and_forbid_lazy_loading(model, attribute, inverse):
    relation = inspect(model).relationships[attribute]
    assert relation.back_populates == inverse
    assert relation.lazy == "raise"
    assert relation.mapper.relationships[inverse].back_populates == attribute


def test_profile_is_scalar_and_authorship_is_an_association_object():
    assert inspect(Cliente).relationships["perfil"].uselist is False
    assert inspect(Libro).relationships["autorias"].mapper.class_ is LibroAutor
    assert {c.name for c in LibroAutor.__table__.primary_key} == {"libro_id", "autor_id"}
    assert Libro.__table__.c.genero_id.nullable is True
    assert Libro.__table__.c.editorial_id.nullable is False
    assert "delete-orphan" in inspect(Venta).relationships["renglones"].cascade


@pytest.mark.parametrize(
    "model, column, precision",
    [
        (Libro, "precio", 10),
        (Venta, "total", 12),
        (RenglonVenta, "precio_unitario", 10),
    ],
)
def test_money_uses_exact_decimal_columns(model, column, precision):
    sql_type = model.__table__.c[column].type
    assert isinstance(sql_type, Numeric)
    assert (sql_type.precision, sql_type.scale, sql_type.asdecimal) == (precision, 2, True)
    assert model.model_fields[column].annotation is Decimal


def test_sale_timestamp_is_timezone_aware():
    sale = Venta(cliente_id=1, total=Decimal("0.00"))
    assert Venta.__table__.c.fecha.type.timezone is True
    assert sale.fecha.utcoffset() is not None


@pytest.mark.parametrize("role, order", [("autor", 1), ("traductor", 3)])
def test_authorship_retains_relationship_data_and_synchronizes_both_ends(role, order):
    author = Autor(nombre="Autora", nacionalidad="Argentina")
    book = Libro(isbn="978-test", titulo="Libro", precio=Decimal("10.10"), stock=0, editorial_id=1)
    authorship = LibroAutor(autor=author, rol=role, orden=order)
    book.autorias.append(authorship)

    assert authorship.libro is book
    assert author.autorias == [authorship]
    assert (book.autorias[0].rol, book.autorias[0].orden) == (role, order)


@pytest.mark.parametrize("quantity, price", [(1, "10.10"), (3, "12.50")])
def test_sale_composition_keeps_lines_and_exact_historical_prices(quantity, price):
    line = RenglonVenta(libro_id=1, cantidad=quantity, precio_unitario=Decimal(price))
    sale = Venta(cliente_id=1, total=quantity * Decimal(price), renglones=[line])

    assert line.venta is sale
    assert sale.renglones == [line]
    assert line.precio_unitario == Decimal(price)
    assert sale.total == Decimal(price) * quantity
