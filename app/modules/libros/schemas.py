from decimal import Decimal
from typing import Annotated, ClassVar, Literal, Self

from pydantic import StringConstraints, model_validator
from sqlmodel import Field

from app.core.schemas import MAX_INTEGER, PartialDTO, PositiveId, StrictDTO
from app.modules.autores.schemas import AutorRead
from app.modules.editoriales.schemas import EditorialRead
from app.modules.generos.schemas import GeneroRead

ISBN = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Titulo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Precio = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
Stock = Annotated[int, Field(ge=0, le=MAX_INTEGER)]
Rol = Literal["autor", "coautor", "traductor", "ilustrador"]


class AutoriaCreate(StrictDTO):
    autor_id: PositiveId
    rol: Rol
    orden: int = Field(ge=1, le=MAX_INTEGER)


def validar_autores(autores: list[AutoriaCreate] | None) -> None:
    if autores is not None and len({autor.autor_id for autor in autores}) != len(autores):
        raise ValueError("Un autor no puede aparecer dos veces en el mismo libro.")


class LibroCreate(StrictDTO):
    isbn: ISBN
    titulo: Titulo
    precio: Precio
    stock: Stock
    editorial_id: PositiveId
    genero_id: PositiveId | None = None
    autores: list[AutoriaCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def autores_unicos(self) -> Self:
        validar_autores(self.autores)
        return self


class LibroUpdate(PartialDTO):
    nullable_fields: ClassVar[frozenset[str]] = frozenset({"genero_id"})
    isbn: ISBN | None = None
    titulo: Titulo | None = None
    precio: Precio | None = None
    stock: Stock | None = None
    editorial_id: PositiveId | None = None
    genero_id: PositiveId | None = None
    autores: list[AutoriaCreate] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def autores_unicos(self) -> Self:
        validar_autores(self.autores)
        return self


class AutoriaRead(StrictDTO):
    autor_id: int
    autor: AutorRead
    rol: Rol
    orden: int


class LibroListRead(StrictDTO):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int
    genero_id: int | None
    editorial: EditorialRead
    genero: GeneroRead | None


class LibroRead(LibroListRead):
    autores: list[AutoriaRead]


class LibroDeAutorRead(StrictDTO):
    libro: LibroListRead
    rol: Rol
    orden: int
