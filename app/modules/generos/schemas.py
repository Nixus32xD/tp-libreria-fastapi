from app.core.schemas import Nombre, StrictDTO


class GeneroCreate(StrictDTO):
    nombre: Nombre


class GeneroRead(StrictDTO):
    id: int
    nombre: str
