from typing import Annotated

from pydantic import EmailStr, StringConstraints

from app.core.schemas import Nombre, PartialDTO, StrictDTO

Telefono = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Direccion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=250)]


class ClienteCreate(StrictDTO):
    nombre: Nombre
    email: EmailStr


class ClienteUpdate(PartialDTO):
    nombre: Nombre | None = None
    email: EmailStr | None = None


class PerfilCreate(StrictDTO):
    telefono: Telefono
    direccion: Direccion


class PerfilRead(StrictDTO):
    id: int
    cliente_id: int
    telefono: str
    direccion: str


class ClienteRead(StrictDTO):
    id: int
    nombre: str
    email: EmailStr
    perfil: PerfilRead | None
