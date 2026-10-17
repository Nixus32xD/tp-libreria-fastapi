from fastapi import APIRouter

from app.core.database import SessionDependency
from app.core.routing import Identifier, Limit, Offset
from app.modules.autores import service
from app.modules.autores.schemas import AutorCreate, AutorRead, AutorUpdate
from app.modules.libros import service as libros_service
from app.modules.libros.schemas import LibroDeAutorRead

router = APIRouter(prefix="/autores", tags=["autores"])


@router.post("/", response_model=AutorRead, status_code=201)
async def crear(datos: AutorCreate, session: SessionDependency):
    return await service.crear(session, datos)


@router.get("/", response_model=list[AutorRead])
async def listar(session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return await service.listar(session, limit, offset)


@router.get("/{id}", response_model=AutorRead)
async def obtener(id: Identifier, session: SessionDependency):
    return await service.obtener(session, id)


@router.patch("/{id}", response_model=AutorRead)
async def actualizar(id: Identifier, datos: AutorUpdate, session: SessionDependency):
    return await service.actualizar(session, id, datos)


@router.get("/{id}/libros", response_model=list[LibroDeAutorRead])
async def libros(id: Identifier, session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    await service.obtener(session, id)
    return await libros_service.listar_por_autor(session, id, limit, offset)
