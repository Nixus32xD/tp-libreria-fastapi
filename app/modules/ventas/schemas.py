from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import EmailStr, model_validator
from sqlmodel import Field

from app.core.schemas import MAX_INTEGER, PositiveId, StrictDTO


class RenglonCreate(StrictDTO):
    libro_id: PositiveId
    cantidad: int = Field(gt=0, le=MAX_INTEGER)


class VentaCreate(StrictDTO):
    cliente_id: PositiveId
    renglones: list[RenglonCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def libros_unicos(self) -> Self:
        if len({renglon.libro_id for renglon in self.renglones}) != len(self.renglones):
            raise ValueError("Un libro no puede aparecer en dos renglones de la venta.")
        return self


class ClienteVentaRead(StrictDTO):
    id: int
    nombre: str
    email: EmailStr


class RenglonRead(StrictDTO):
    libro_id: int
    titulo: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class VentaRead(StrictDTO):
    id: int
    cliente_id: int
    fecha: datetime
    total: Decimal
    cliente: ClienteVentaRead
    renglones: list[RenglonRead]
