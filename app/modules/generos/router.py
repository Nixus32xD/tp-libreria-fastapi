from fastapi import APIRouter

from app.core.database import SessionDependency
from app.core.routing import Identifier, Limit, Offset
from app.modules.generos import service
from app.modules.generos.schemas import GeneroCreate, GeneroRead
from app.modules.libros import service as libros_service
from app.modules.libros.schemas import LibroListRead

router = APIRouter(prefix="/generos", tags=["generos"])


@router.post("/", response_model=GeneroRead, status_code=201)
async def crear(datos: GeneroCreate, session: SessionDependency):
    return await service.crear(session, datos)


@router.get("/", response_model=list[GeneroRead])
async def listar(session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return await service.listar(session, limit, offset)


@router.get("/{id}/libros", response_model=list[LibroListRead])
async def libros(id: Identifier, session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    await service.obtener(session, id)
    return await libros_service.listar(session, limit, offset, genero_id=id)
