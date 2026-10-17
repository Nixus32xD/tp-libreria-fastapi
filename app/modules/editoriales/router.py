from fastapi import APIRouter

from app.core.database import SessionDependency
from app.core.routing import Identifier, Limit, Offset
from app.modules.editoriales import service
from app.modules.editoriales.schemas import EditorialCreate, EditorialRead, EditorialUpdate
from app.modules.libros import service as libros_service
from app.modules.libros.schemas import LibroListRead

router = APIRouter(prefix="/editoriales", tags=["editoriales"])


@router.post("/", response_model=EditorialRead, status_code=201)
async def crear(datos: EditorialCreate, session: SessionDependency):
    return await service.crear(session, datos)


@router.get("/", response_model=list[EditorialRead])
async def listar(session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return await service.listar(session, limit, offset)


@router.get("/{id}", response_model=EditorialRead)
async def obtener(id: Identifier, session: SessionDependency):
    return await service.obtener(session, id)


@router.patch("/{id}", response_model=EditorialRead)
async def actualizar(id: Identifier, datos: EditorialUpdate, session: SessionDependency):
    return await service.actualizar(session, id, datos)


@router.get("/{id}/libros", response_model=list[LibroListRead])
async def libros(id: Identifier, session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    await service.obtener(session, id)
    return await libros_service.listar(session, limit, offset, editorial_id=id)
