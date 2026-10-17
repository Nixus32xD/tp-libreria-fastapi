from app.core.schemas import Nombre, Pais, PartialDTO, StrictDTO


class EditorialCreate(StrictDTO):
    nombre: Nombre
    pais: Pais


class EditorialUpdate(PartialDTO):
    nombre: Nombre | None = None
    pais: Pais | None = None


class EditorialRead(StrictDTO):
    id: int
    nombre: str
    pais: str
