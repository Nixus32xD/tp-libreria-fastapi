from fastapi import APIRouter

from app.core.database import SessionDependency
from app.core.routing import Identifier, Limit, Offset
from app.modules.clientes import service
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)
from app.modules.ventas import service as ventas_service
from app.modules.ventas.schemas import VentaRead

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post("/", response_model=ClienteRead, status_code=201)
async def crear(datos: ClienteCreate, session: SessionDependency):
    return await service.crear(session, datos)


@router.get("/", response_model=list[ClienteRead])
async def listar(session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return await service.listar(session, limit, offset)


@router.get("/{id}", response_model=ClienteRead)
async def obtener(id: Identifier, session: SessionDependency):
    return await service.obtener(session, id)


@router.patch("/{id}", response_model=ClienteRead)
async def actualizar(id: Identifier, datos: ClienteUpdate, session: SessionDependency):
    return await service.actualizar(session, id, datos)


@router.post("/{id}/perfil", response_model=PerfilRead, status_code=201)
async def crear_perfil(id: Identifier, datos: PerfilCreate, session: SessionDependency):
    return await service.crear_perfil(session, id, datos)


@router.get("/{id}/ventas", response_model=list[VentaRead])
async def ventas(id: Identifier, session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    await service.obtener(session, id)
    return await ventas_service.listar(session, limit, offset, cliente_id=id)
