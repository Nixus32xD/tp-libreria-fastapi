from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel


class Venta(SQLModel, table=True):
    __tablename__ = "venta"
    __table_args__ = (CheckConstraint("total >= 0", name="ck_venta_total_no_negativo"),)

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    fecha: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    total: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))

    cliente: "Cliente" = Relationship(  # noqa: F821
        back_populates="ventas", sa_relationship_kwargs={"lazy": "raise"}
    )
    renglones: list["RenglonVenta"] = Relationship(
        back_populates="venta",
        sa_relationship_kwargs={"lazy": "raise", "cascade": "all, delete-orphan"},
    )


class RenglonVenta(SQLModel, table=True):
    __tablename__ = "renglon_venta"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_renglon_cantidad_positiva"),
        CheckConstraint("precio_unitario > 0", name="ck_renglon_precio_positivo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="venta.id", index=True)
    libro_id: int = Field(foreign_key="libro.id", index=True)
    cantidad: int
    precio_unitario: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

    venta: "Venta" = Relationship(
        back_populates="renglones", sa_relationship_kwargs={"lazy": "raise"}
    )
    libro: "Libro" = Relationship(  # noqa: F821
        back_populates="renglones", sa_relationship_kwargs={"lazy": "raise"}
    )
