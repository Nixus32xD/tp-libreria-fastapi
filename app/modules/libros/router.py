from typing import Annotated

from fastapi import APIRouter, Query

from app.core.database import SessionDependency
from app.core.routing import Identifier, Limit, Offset
from app.core.schemas import MAX_INTEGER
from app.modules.libros import service
from app.modules.libros.schemas import LibroCreate, LibroListRead, LibroRead, LibroUpdate

router = APIRouter(prefix="/libros", tags=["libros"])


@router.post("/", response_model=LibroRead, status_code=201)
async def crear(datos: LibroCreate, session: SessionDependency):
    return await service.crear(session, datos)


@router.get("/", response_model=list[LibroListRead])
async def listar(
    session: SessionDependency,
    limit: Limit = 20,
    offset: Offset = 0,
    titulo: Annotated[str | None, Query(max_length=200)] = None,
    genero_id: Annotated[int | None, Query(gt=0, le=MAX_INTEGER)] = None,
):
    return await service.listar(session, limit, offset, titulo=titulo, genero_id=genero_id)


@router.get("/{id}", response_model=LibroRead)
async def obtener(id: Identifier, session: SessionDependency):
    return await service.obtener(session, id)


@router.patch("/{id}", response_model=LibroRead)
async def actualizar(id: Identifier, datos: LibroUpdate, session: SessionDependency):
    return await service.actualizar(session, id, datos)
