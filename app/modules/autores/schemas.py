from app.core.schemas import Nombre, Pais, PartialDTO, StrictDTO


class AutorCreate(StrictDTO):
    nombre: Nombre
    nacionalidad: Pais


class AutorUpdate(PartialDTO):
    nombre: Nombre | None = None
    nacionalidad: Pais | None = None


class AutorRead(StrictDTO):
    id: int
    nombre: str
    nacionalidad: str
